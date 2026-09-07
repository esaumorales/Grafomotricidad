"""
Pipeline de preprocesamiento (Etapa 1 de la arquitectura).

foto -> orientar -> corregir perspectiva/inclinación -> normalizar iluminación ->
binarizar -> aislar la figura -> registrar respecto a la plantilla del CUMANIN-2.

Cada paso es una función pura para poder testear y calibrar por separado.
La implementación es una BASE con OpenCV/scikit-image; hay que ajustar umbrales
con las figuras y las fotos reales del estudio.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class PreprocResultado:
    figura_bin: np.ndarray          # binaria (0/255), lado normalizado, registrada a plantilla
    registro_ok: bool               # el registro convergió
    escala: float                   # factor de escala aplicado en el registro
    rotacion_deg: float             # rotación estimada respecto a la plantilla
    traslacion_px: tuple[float, float]
    calidad: float                  # 0..1: heurística de calidad de la imagen de entrada
    aviso: str | None = None        # p.ej. "foto borrosa", "registro no convergió"


# --------------------------------------------------------------------------- #
def cargar_y_orientar(path: str) -> np.ndarray:
    """Lee la imagen respetando la orientación EXIF y la pasa a escala de grises."""
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(path)
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def corregir_perspectiva(gris: np.ndarray) -> np.ndarray:
    """Detecta el rectángulo de la hoja y rectifica la perspectiva.

    Base: contorno cuadrilátero de mayor área -> warpPerspective a un rectángulo.
    Si no encuentra un cuadrilátero claro, devuelve la imagen sin cambios.
    """
    bordes = cv2.Canny(cv2.GaussianBlur(gris, (5, 5), 0), 50, 150)
    contornos, _ = cv2.findContours(bordes, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contornos:
        return gris
    c = max(contornos, key=cv2.contourArea)
    peri = cv2.arcLength(c, True)
    aprox = cv2.approxPolyDP(c, 0.02 * peri, True)
    if len(aprox) != 4 or cv2.contourArea(c) < 0.2 * gris.size:
        return gris
    src = _ordenar_esquinas(aprox.reshape(4, 2).astype("float32"))
    w = int(max(np.linalg.norm(src[0] - src[1]), np.linalg.norm(src[2] - src[3])))
    h = int(max(np.linalg.norm(src[0] - src[3]), np.linalg.norm(src[1] - src[2])))
    dst = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype="float32")
    M = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(gris, M, (w, h))


def normalizar_iluminacion(gris: np.ndarray) -> np.ndarray:
    """Quita gradientes de luz/sombra: fondo estimado por blur grande y división."""
    fondo = cv2.GaussianBlur(gris, (0, 0), sigmaX=max(gris.shape) / 30)
    norm = cv2.divide(gris, fondo, scale=255)
    return cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(norm)


def binarizar(gris: np.ndarray, metodo: str = "adaptativo") -> np.ndarray:
    if metodo == "otsu":
        _, b = cv2.threshold(gris, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    else:
        b = cv2.adaptiveThreshold(
            gris, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 31, 10
        )
    b = cv2.morphologyEx(b, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))   # quita motas
    return b


def aislar_figura(binaria: np.ndarray, min_area: int = 400) -> np.ndarray:
    """Se queda con la componente de trazo dominante (el dibujo del niño)."""
    n, lab, stats, _ = cv2.connectedComponentsWithStats(binaria, connectivity=8)
    if n <= 1:
        return binaria
    idx = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    if stats[idx, cv2.CC_STAT_AREA] < min_area:
        return binaria
    return np.where(lab == idx, 255, 0).astype(np.uint8)


def registrar_a_plantilla(
    figura: np.ndarray, plantilla: np.ndarray, modo: str = "similaridad", lado: int = 512
) -> tuple[np.ndarray, dict]:
    """
    Alinea la figura del niño con la plantilla de referencia.

    Base: momentos + ECC (Enhanced Correlation Coefficient) de OpenCV para estimar
    una transformación de similaridad (o afín). Devuelve la figura re-muestreada al
    lienzo de la plantilla y los parámetros del registro.
    """
    figura = _encajar_en_lienzo(figura, lado)
    plantilla = _encajar_en_lienzo(plantilla, lado)
    warp = np.eye(2, 3, dtype=np.float32)
    modo_cv = cv2.MOTION_EUCLIDEAN if modo == "similaridad" else cv2.MOTION_AFFINE
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-5)
    try:
        cc, warp = cv2.findTransformECC(
            plantilla.astype(np.float32) / 255,
            figura.astype(np.float32) / 255,
            warp, modo_cv, crit, None, 5,
        )
        ok = cc > 0.2
    except cv2.error:
        ok = False
    alineada = cv2.warpAffine(figura, warp, (lado, lado), flags=cv2.INTER_NEAREST)
    sx = float(np.hypot(warp[0, 0], warp[1, 0]))
    ang = float(np.degrees(np.arctan2(warp[1, 0], warp[0, 0])))
    return alineada, {
        "ok": ok, "escala": sx, "rotacion_deg": ang,
        "traslacion_px": (float(warp[0, 2]), float(warp[1, 2])),
    }


def calidad_imagen(gris: np.ndarray) -> float:
    """Heurística 0..1: nitidez (varianza del laplaciano) + contraste."""
    nitidez = cv2.Laplacian(gris, cv2.CV_64F).var()
    contraste = gris.std()
    s = min(nitidez / 300.0, 1.0) * 0.7 + min(contraste / 60.0, 1.0) * 0.3
    return round(float(s), 3)


# --------------------------------------------------------------------------- #
def preprocesar_figura(
    ruta_foto: str, plantilla_bin: np.ndarray, cfg: dict | None = None
) -> PreprocResultado:
    """Ejecuta todo el pipeline sobre una foto de una figura."""
    cfg = cfg or {}
    lado = int(cfg.get("lado_normalizado_px", 512))
    metodo_bin = cfg.get("umbral_binarizado", "adaptativo")
    modo_reg = cfg.get("registro", "similaridad")
    min_area = int(cfg.get("min_area_figura_px", 400))

    gris = cargar_y_orientar(ruta_foto)
    q = calidad_imagen(gris)
    gris = corregir_perspectiva(gris)
    gris = normalizar_iluminacion(gris)
    binaria = binarizar(gris, metodo_bin)
    figura = aislar_figura(binaria, min_area)
    alineada, reg = registrar_a_plantilla(figura, plantilla_bin, modo_reg, lado)

    aviso = None
    if q < 0.35:
        aviso = "foto poco nítida"
    elif not reg["ok"]:
        aviso = "el registro con la plantilla no convergió"

    return PreprocResultado(
        figura_bin=alineada,
        registro_ok=reg["ok"],
        escala=reg["escala"],
        rotacion_deg=reg["rotacion_deg"],
        traslacion_px=reg["traslacion_px"],
        calidad=q,
        aviso=aviso,
    )


# --------------------------------------------------------------------------- #
def _ordenar_esquinas(pts: np.ndarray) -> np.ndarray:
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]],
                    dtype="float32")


def _encajar_en_lienzo(binaria: np.ndarray, lado: int) -> np.ndarray:
    ys, xs = np.where(binaria > 0)
    if len(xs) == 0:
        return cv2.resize(binaria, (lado, lado), interpolation=cv2.INTER_NEAREST)
    recorte = binaria[ys.min(): ys.max() + 1, xs.min(): xs.max() + 1]
    h, w = recorte.shape
    esc = (lado * 0.8) / max(h, w)
    rs = cv2.resize(recorte, (max(1, int(w * esc)), max(1, int(h * esc))),
                    interpolation=cv2.INTER_NEAREST)
    lienzo = np.zeros((lado, lado), np.uint8)
    y0 = (lado - rs.shape[0]) // 2
    x0 = (lado - rs.shape[1]) // 2
    lienzo[y0: y0 + rs.shape[0], x0: x0 + rs.shape[1]] = rs
    return lienzo
