"""
Degradaciones sintéticas de la foto para la prueba de robustez (ambos modelos).

Simulan lo que pasa al fotografiar en el aula a mano: sombra, desenfoque, hoja
inclinada y exceso/falta de luz. Se aplican a la FOTO en escala de grises, antes
de cualquier preprocesamiento, para que los dos modelos reciban lo mismo.

Son evidencia más débil que la doble foto real (controlada vs. aula); se reportan
por separado.
"""
from __future__ import annotations

import cv2
import numpy as np

NIVELES = {"leve": 0, "moderada": 1, "fuerte": 2}

# Subir este número si cambia cualquier degradación: invalida la caché de robustez de A.
VERSION = 1


def sombra(gris: np.ndarray, nivel: int, rng: np.random.Generator) -> np.ndarray:
    """Banda de sombra con borde difuso (mano o celular tapando la luz)."""
    h, w = gris.shape
    fuerza = (0.25, 0.4, 0.55)[nivel]
    yy, xx = np.mgrid[0:h, 0:w]
    ang = rng.uniform(0, np.pi)
    d = (xx - w / 2) * np.cos(ang) + (yy - h / 2) * np.sin(ang) - rng.uniform(-0.2, 0.2) * w
    mascara = 1 / (1 + np.exp(-d / (0.05 * max(h, w))))
    factor = 1 - fuerza * mascara
    return np.clip(gris.astype(np.float32) * factor, 0, 255).astype(np.uint8)


def desenfoque(gris: np.ndarray, nivel: int, rng: np.random.Generator) -> np.ndarray:
    sigma = (1.0, 2.0, 3.5)[nivel]
    return cv2.GaussianBlur(gris, (0, 0), sigma)


def inclinacion(gris: np.ndarray, nivel: int, rng: np.random.Generator) -> np.ndarray:
    """Perspectiva: la hoja fotografiada de lado (no rota la figura en el plano)."""
    h, w = gris.shape
    t = (0.04, 0.08, 0.12)[nivel]
    src = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    dx, dy = t * w, t * h
    lado = rng.integers(4)
    dst = src.copy()
    # un lado de la hoja se aleja de la cámara: sus dos esquinas se desplazan hacia dentro
    desplazamientos = {0: [(0, [dx, dy]), (1, [-dx, dy])],      # arriba
                       1: [(1, [-dx, dy]), (2, [-dx, -dy])],    # derecha
                       2: [(2, [-dx, -dy]), (3, [dx, -dy])],    # abajo
                       3: [(3, [dx, -dy]), (0, [dx, dy])]}      # izquierda
    for esquina, d in desplazamientos[int(lado)]:
        dst[esquina] += d
    M = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(gris, M, (w, h), borderValue=int(np.median(gris)))


def brillo(gris: np.ndarray, nivel: int, rng: np.random.Generator) -> np.ndarray:
    """Sobreexposición o subexposición con pérdida de contraste."""
    delta = (35, 60, 85)[nivel] * (1 if rng.random() < 0.5 else -1)
    contraste = (0.85, 0.7, 0.55)[nivel]
    x = (gris.astype(np.float32) - 128) * contraste + 128 + delta
    return np.clip(x, 0, 255).astype(np.uint8)


DEGRADACIONES = {"sombra": sombra, "desenfoque": desenfoque,
                 "inclinacion": inclinacion, "brillo": brillo}


def degradar(gris: np.ndarray, tipo: str, nivel: str, semilla: int) -> np.ndarray:
    rng = np.random.default_rng(semilla)
    return DEGRADACIONES[tipo](gris, NIVELES[nivel], rng)
