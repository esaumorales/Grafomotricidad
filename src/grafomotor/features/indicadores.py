"""
Los 6 indicadores geométricos. Cada función devuelve:

    (valor_norm, raw)

donde `valor_norm` ∈ [0, 1] con la convención  1 = igual que el modelo, 0 = muy alejado.
`raw` es el número crudo para el panel técnico del especialista.

Todas reciben imágenes binarias (0/255) del MISMO lado, ya registradas a la plantilla.
Implementación base: hay que calibrar tolerancias con las figuras reales del CUMANIN-2.
"""
from __future__ import annotations

import cv2
import numpy as np
from skimage.morphology import skeletonize


def _contorno_mayor(bin_: np.ndarray) -> np.ndarray | None:
    cs, _ = cv2.findContours(bin_, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    return max(cs, key=cv2.contourArea) if cs else None


def _clip01(x: float) -> float:
    return float(max(0.0, min(1.0, x)))


# 1 -------------------------------------------------------------------------- #
def precision_modelo(figura: np.ndarray, plantilla: np.ndarray, tol_px: int = 6) -> tuple[float, float]:
    """Parecido general: IoU entre el trazo del niño y el del modelo, con tolerancia."""
    k = np.ones((tol_px, tol_px), np.uint8)
    a = cv2.dilate(figura, k) > 0
    b = cv2.dilate(plantilla, k) > 0
    inter = np.logical_and(a, b).sum()
    union = np.logical_or(a, b).sum()
    iou = inter / union if union else 0.0
    return _clip01(iou), float(iou)


# 2 -------------------------------------------------------------------------- #
def vertices(figura: np.ndarray, n_esperados: int) -> tuple[float, int]:
    """Nº de esquinas detectadas frente a las esperadas por el modelo."""
    c = _contorno_mayor(figura)
    if c is None:
        return 0.0, 0
    peri = cv2.arcLength(c, True)
    aprox = cv2.approxPolyDP(c, 0.02 * peri, True)
    n = len(aprox) if n_esperados > 0 else 0
    if n_esperados == 0:                      # figura sin vértices (círculo)
        # penaliza si aparecen esquinas marcadas
        return _clip01(1.0 - len(aprox) / 8.0), len(aprox)
    err = abs(n - n_esperados) / n_esperados
    return _clip01(1.0 - err), n


# 3 -------------------------------------------------------------------------- #
def error_angular(figura: np.ndarray, plantilla: np.ndarray) -> tuple[float, float]:
    """Diferencia media entre los ángulos internos del niño y los del modelo (grados)."""
    ang_f = _angulos_internos(figura)
    ang_p = _angulos_internos(plantilla)
    if not ang_f or not ang_p:
        return 0.5, float("nan")
    m = min(len(ang_f), len(ang_p))
    ang_f, ang_p = sorted(ang_f)[:m], sorted(ang_p)[:m]
    err = float(np.mean(np.abs(np.array(ang_f) - np.array(ang_p))))
    return _clip01(1.0 - err / 45.0), err


# 4 -------------------------------------------------------------------------- #
def cierre(figura: np.ndarray) -> tuple[float, int]:
    """Cierre: cuenta extremos libres del esqueleto (una figura cerrada no tiene)."""
    sk = skeletonize(figura > 0)
    vecinos = cv2.filter2D(sk.astype(np.uint8), -1, np.ones((3, 3), np.uint8)) - 1
    n_extremos = int(np.sum((sk) & (vecinos == 1)))
    # 0 extremos = perfectamente cerrada; se degrada con cada extremo libre.
    return _clip01(1.0 - n_extremos / 4.0), n_extremos


# 5 -------------------------------------------------------------------------- #
def intersecciones(figura: np.ndarray, plantilla: np.ndarray, n_esperadas: int) -> tuple[float, float]:
    """Cruces de línea: distancia entre los cruces del niño y los esperados."""
    if n_esperadas == 0:
        cruces_f = _puntos_cruce(figura)
        return _clip01(1.0 - len(cruces_f) / 3.0), float(len(cruces_f))
    cf, cp = _puntos_cruce(figura), _puntos_cruce(plantilla)
    if not cf or not cp:
        return 0.0, float("inf")
    d = np.linalg.norm(np.array(cf[0]) - np.array(cp[0]))
    diag = float(np.hypot(*figura.shape))
    return _clip01(1.0 - d / (0.15 * diag)), float(d)


# 6 -------------------------------------------------------------------------- #
def proporcion(figura: np.ndarray, plantilla: np.ndarray) -> tuple[float, float]:
    """Tamaño de las partes: relación de aspecto del niño vs. la del modelo."""
    rf = _aspecto(figura)
    rp = _aspecto(plantilla)
    if rf is None or rp is None or rp == 0:
        return 0.5, float("nan")
    razon = rf / rp
    err = abs(np.log(razon))                # simétrico: 2x y 0.5x penalizan igual
    return _clip01(1.0 - err / np.log(2)), float(razon)


# --------------------------------------------------------------------------- #
def _angulos_internos(bin_: np.ndarray) -> list[float]:
    c = _contorno_mayor(bin_)
    if c is None:
        return []
    peri = cv2.arcLength(c, True)
    p = cv2.approxPolyDP(c, 0.02 * peri, True).reshape(-1, 2).astype(float)
    if len(p) < 3:
        return []
    ang = []
    for i in range(len(p)):
        a, b, c_ = p[i - 1], p[i], p[(i + 1) % len(p)]
        v1, v2 = a - b, c_ - b
        cos = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-9)
        ang.append(float(np.degrees(np.arccos(np.clip(cos, -1, 1)))))
    return ang


def _puntos_cruce(bin_: np.ndarray) -> list[tuple[int, int]]:
    sk = skeletonize(bin_ > 0).astype(np.uint8)
    vecinos = cv2.filter2D(sk, -1, np.ones((3, 3), np.uint8)) - 1
    ys, xs = np.where((sk == 1) & (vecinos >= 3))
    return list(zip(xs.tolist(), ys.tolist()))


def _aspecto(bin_: np.ndarray) -> float | None:
    ys, xs = np.where(bin_ > 0)
    if len(xs) == 0:
        return None
    w = xs.max() - xs.min() + 1
    h = ys.max() - ys.min() + 1
    return w / h
