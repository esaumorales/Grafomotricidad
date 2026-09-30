"""
Preprocesamiento MÍNIMO para el modelo B (a diferencia del pipeline del modelo A, aquí
no se binariza, no se aísla el trazo ni se registra contra la plantilla):

  1. escala de grises
  2. corregir la perspectiva de la hoja (misma función que el modelo A)
  3. recortar la figura: caja del trazo con margen amplio, hecha cuadrada
  4. reescalar a 224 × 224

La imagen se guarda en gris; se copia a 3 canales al construir el tensor
(las redes preentrenadas en ImageNet esperan 3 canales).
"""
from __future__ import annotations

import cv2
import numpy as np

from grafomotor.preprocessing.pipeline import corregir_perspectiva

LADO = 224


def caja_del_trazo(gris: np.ndarray) -> tuple[int, int, int, int] | None:
    """Caja (x0, y0, x1, y1) de la tinta. Solo se usa para recortar, no llega a la red."""
    suave = cv2.GaussianBlur(gris, (5, 5), 0)
    _, tinta = cv2.threshold(suave, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    tinta = cv2.morphologyEx(tinta, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    # descartar un marco de 2 % (bordes de la hoja / sombras del contorno)
    h, w = tinta.shape
    m = max(2, int(0.02 * max(h, w)))
    tinta[:m], tinta[-m:], tinta[:, :m], tinta[:, -m:] = 0, 0, 0, 0
    ys, xs = np.where(tinta > 0)
    if len(xs) < 30:
        return None
    x0, x1 = np.percentile(xs, [0.5, 99.5]).astype(int)
    y0, y1 = np.percentile(ys, [0.5, 99.5]).astype(int)
    return int(x0), int(y0), int(x1), int(y1)


def recorte_cuadrado(gris: np.ndarray, caja, margen: float = 0.15) -> np.ndarray:
    x0, y0, x1, y1 = caja
    lado = int(max(x1 - x0, y1 - y0) * (1 + 2 * margen)) + 1
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    fondo = int(np.median(gris))
    lienzo = np.full((lado, lado), fondo, np.uint8)
    sx0, sy0 = cx - lado // 2, cy - lado // 2
    ax0, ay0 = max(0, sx0), max(0, sy0)
    ax1, ay1 = min(gris.shape[1], sx0 + lado), min(gris.shape[0], sy0 + lado)
    lienzo[ay0 - sy0: ay1 - sy0, ax0 - sx0: ax1 - sx0] = gris[ay0:ay1, ax0:ax1]
    return lienzo


def preparar_gris(gris: np.ndarray, lado: int = LADO) -> tuple[np.ndarray, str | None]:
    """Foto en gris -> recorte 224×224 en gris. Devuelve (imagen, aviso)."""
    gris = corregir_perspectiva(gris)
    caja = caja_del_trazo(gris)
    aviso = None
    if caja is None:
        aviso = "no se encontró trazo; se usa la foto entera"
        caja = (0, 0, gris.shape[1] - 1, gris.shape[0] - 1)
    rec = recorte_cuadrado(gris, caja)
    return cv2.resize(rec, (lado, lado), interpolation=cv2.INTER_AREA), aviso


def preparar_imagen(ruta: str, lado: int = LADO) -> tuple[np.ndarray, str | None]:
    gris = cv2.imread(str(ruta), cv2.IMREAD_GRAYSCALE)
    if gris is None:
        raise FileNotFoundError(ruta)
    return preparar_gris(gris, lado)


def mascara_trazo(img224: np.ndarray, dilatar_px: int = 6) -> np.ndarray:
    """Máscara booleana del trazo (dilatada) sobre la imagen ya recortada, para Grad-CAM."""
    _, t = cv2.threshold(cv2.GaussianBlur(img224, (3, 3), 0), 0, 255,
                         cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    k = np.ones((2 * dilatar_px + 1, 2 * dilatar_px + 1), np.uint8)
    return cv2.dilate(t, k) > 0
