"""
Aumento de datos seguro para la etiqueta.

El CUMANIN-2 puntúa rotación, cierre, proporción y ángulos: rotar mucho o voltear
una figura CAMBIA su puntaje. Aquí solo se permiten transformaciones que no alteran
los criterios de corrección:

  - deformación elástica leve (temblor de trazo natural)
  - variación del grosor del trazo (lápiz más/menos apretado)
  - brillo/contraste sobre la foto (antes de binarizar)
  - perspectiva mínima (<= 3°), opcional

PROHIBIDO: rotaciones > ~5°, volteos (flip), zoom que cambie proporciones.
"""
from __future__ import annotations

import cv2
import numpy as np

_RNG = np.random.default_rng(20260101)


def deformacion_elastica(bin_: np.ndarray, alpha: float = 8.0, sigma: float = 6.0) -> np.ndarray:
    h, w = bin_.shape
    dx = cv2.GaussianBlur((_RNG.random((h, w)) * 2 - 1).astype(np.float32), (0, 0), sigma) * alpha
    dy = cv2.GaussianBlur((_RNG.random((h, w)) * 2 - 1).astype(np.float32), (0, 0), sigma) * alpha
    yy, xx = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
    mapx = (xx + dx).astype(np.float32)
    mapy = (yy + dy).astype(np.float32)
    return cv2.remap(bin_, mapx, mapy, cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT)


def variar_grosor(bin_: np.ndarray) -> np.ndarray:
    k = int(_RNG.integers(1, 3))
    op = cv2.dilate if _RNG.random() < 0.5 else cv2.erode
    return op(bin_, np.ones((k, k), np.uint8))


def brillo_contraste(gris: np.ndarray) -> np.ndarray:
    a = 1.0 + float(_RNG.uniform(-0.2, 0.2))   # contraste
    b = float(_RNG.uniform(-20, 20))            # brillo
    return cv2.convertScaleAbs(gris, alpha=a, beta=b)


def aumentar(bin_: np.ndarray, n: int, transformaciones: list[str]) -> list[np.ndarray]:
    """Genera `n` variantes de una figura binaria manteniendo su etiqueta."""
    salida = []
    for _ in range(n):
        x = bin_.copy()
        if "elastica_leve" in transformaciones:
            x = deformacion_elastica(x)
        if "grosor_trazo" in transformaciones:
            x = variar_grosor(x)
        # "brillo_contraste" se aplica antes de binarizar; se deja documentado.
        salida.append(x)
    return salida
