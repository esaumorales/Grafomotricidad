"""
Plantillas de referencia de las 15 figuras de Visopercepción (CUMANIN original,
Apéndice C del manual), trazadas como VECTORES a partir del criterio de corrección.

No son un escaneo del manual (no se versiona por derechos de autor). Si el equipo
consigue la digitalización oficial, basta con sustituir los PNG 1:1
(data/templates/F01.png ... F15.png).

PNG binario, 512×512, trazo blanco (255) sobre fondo negro (0): el mismo formato que
produce el preprocesamiento del modelo A (`preprocessing/pipeline.py`).
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import cv2
import numpy as np

from grafomotor.config import Config
from grafomotor.logs import obtener_logger

log = obtener_logger(__name__)

L = 512
M = 96          # margen
G = 5           # grosor de trazo


def _lienzo() -> np.ndarray:
    return np.zeros((L, L), np.uint8)


# F01 --------------------------------------------------------------------- #
def linea_recta() -> np.ndarray:
    im = _lienzo()
    cv2.line(im, (L // 2, M), (L // 2, L - M), 255, G)
    return im


# F02 --------------------------------------------------------------------- #
def dos_lineas_horizontales() -> np.ndarray:
    im = _lienzo()
    y1, y2 = L // 2 - 70, L // 2 + 70
    cv2.line(im, (M, y1), (L - M, y1), 255, G)
    cv2.line(im, (M + 40, y2), (L - M - 40, y2), 255, G)
    return im


# F03 --------------------------------------------------------------------- #
def cruz() -> np.ndarray:
    im = _lienzo()
    cv2.line(im, (L // 2, M), (L // 2, L - M), 255, G)
    cv2.line(im, (M, L // 2), (L - M, L // 2), 255, G)
    return im


# F04 --------------------------------------------------------------------- #
def circulo() -> np.ndarray:
    im = _lienzo()
    r = (L - 2 * M) // 2
    cv2.ellipse(im, (L // 2, L // 2), (r, int(r * 0.85)), 0, 0, 360, 255, G)
    return im


# F05 --------------------------------------------------------------------- #
def cuadrado() -> np.ndarray:
    im = _lienzo()
    cv2.rectangle(im, (M, M), (L - M, L - M), 255, G)
    return im


# F06 --------------------------------------------------------------------- #
def triangulo() -> np.ndarray:
    im = _lienzo()
    p = np.array([[L // 2, M], [M, L - M], [L - M, L - M]], np.int32)
    cv2.polylines(im, [p], True, 255, G)
    return im


# F07 --------------------------------------------------------------------- #
def x_aspa() -> np.ndarray:
    im = _lienzo()
    cv2.line(im, (M, M), (L - M, L - M), 255, G)
    cv2.line(im, (L - M, M), (M, L - M), 255, G)
    return im


# F08 --------------------------------------------------------------------- #
def linea_ondulada() -> np.ndarray:
    im = _lienzo()
    xs = np.linspace(M, L - M, 200)
    amp = 60
    ys = L / 2 + amp * np.sin((xs - M) / (L - 2 * M) * 2 * np.pi)
    pts = np.stack([xs, ys], axis=1).astype(np.int32)
    cv2.polylines(im, [pts], False, 255, G)
    return im


# F09 --------------------------------------------------------------------- #
def rectangulo_x() -> np.ndarray:
    im = _lienzo()
    x0, y0, x1, y1 = M, L // 2 - 90, L - M, L // 2 + 90
    cv2.rectangle(im, (x0, y0), (x1, y1), 255, G)
    cv2.line(im, (x0, y0), (x1, y1), 255, G)
    cv2.line(im, (x1, y0), (x0, y1), 255, G)
    return im


# F10 --------------------------------------------------------------------- #
def rombo() -> np.ndarray:
    im = _lienzo()
    p = np.array([[L // 2, M], [L - M, L // 2], [L // 2, L - M], [M, L // 2]], np.int32)
    cv2.polylines(im, [p], True, 255, G)
    return im


# F11 --------------------------------------------------------------------- #
def circulo_triangulo() -> np.ndarray:
    im = _lienzo()
    cy = M + 75
    r = 60
    cv2.circle(im, (L // 2, cy), r, 255, G)
    apex_y = cy + r
    p = np.array([[L // 2, apex_y], [L // 2 - 95, apex_y + 150], [L // 2 + 95, apex_y + 150]],
                 np.int32)
    cv2.polylines(im, [p], True, 255, G)
    return im


# F12 --------------------------------------------------------------------- #
def u_forma() -> np.ndarray:
    """Apéndice C, Figura 12: una recta + una curva CÓNCAVA, tangentes en un punto
    (no superpuestas). Dos trazos en total -> una sola U, no dos lados rectos + arco."""
    im = _lienzo()
    y_base = L - M - 30
    cv2.line(im, (M, y_base), (L - M, y_base), 255, G)
    cx = L // 2
    r = 95
    cy = y_base - r
    cv2.ellipse(im, (cx, cy), (r, r), 0, 0, 180, 255, G)
    return im


# F13 --------------------------------------------------------------------- #
def lazo() -> np.ndarray:
    im = _lienzo()
    cx, cy = L // 2, L // 2
    r = 95
    cv2.ellipse(im, (cx - r, cy), (r, r), 0, -55, 55, 255, G)
    cv2.ellipse(im, (cx + r, cy), (r, r), 0, 125, 235, 255, G)
    return im


# F14 --------------------------------------------------------------------- #
def doble_pico_ondulado() -> np.ndarray:
    """Apéndice C, Figura 14: 2 rectas convergentes arriba (pico) + 1 curva de
    TRES ondulaciones (laterales convexas, central cóncava) secante a cada recta
    en un punto (2 cruces en total, no más)."""
    im = _lienzo()
    apex = (L // 2, M + 35)
    left_end = (M + 20, M + 150)
    right_end = (L - M - 20, M + 150)
    cv2.line(im, left_end, apex, 255, G)
    cv2.line(im, apex, right_end, 255, G)
    xs = np.linspace(M, L - M, 240)
    y_mid = M + 105  # dentro del rango vertical del pico (apex..extremos) para que sea secante
    amp = 50
    ys = y_mid + amp * np.sin(3 * np.pi * (xs - M) / (L - 2 * M))
    pts = np.stack([xs, ys], axis=1).astype(np.int32)
    cv2.polylines(im, [pts], False, 255, G)
    return im


# F15 --------------------------------------------------------------------- #
def cuadrado_circulo() -> np.ndarray:
    im = _lienzo()
    lado = 190
    x0, y0 = M, M
    cv2.rectangle(im, (x0, y0), (x0 + lado, y0 + lado), 255, G)
    ccx, ccy = x0 + lado - 45, y0 + lado - 20
    cv2.circle(im, (ccx, ccy), 105, 255, G)
    return im


GENERADORES: dict[str, Callable[[], np.ndarray]] = {
    "línea recta": linea_recta,
    "dos líneas horizontales": dos_lineas_horizontales,
    "cruz": cruz,
    "círculo": circulo,
    "cuadrado": cuadrado,
    "triángulo": triangulo,
    "x (aspa)": x_aspa,
    "línea ondulada": linea_ondulada,
    "rectángulo con x interna": rectangulo_x,
    "rombo": rombo,
    "círculo + triángulo": circulo_triangulo,
    "u": u_forma,
    "lazo": lazo,
    "doble pico ondulado": doble_pico_ondulado,
    "cuadrado + círculo": cuadrado_circulo,
}


def generar_plantillas(cfg: Config) -> list[Path]:
    """Escribe una plantilla por figura de config.yaml (se elige el generador por nombre)."""
    salida = cfg.ruta("templates")
    salida.mkdir(parents=True, exist_ok=True)
    escritas = []
    for fid, meta in cfg.figuras.items():
        nombre = meta.get("nombre", "")
        generador = GENERADORES.get(nombre)
        if generador is None:
            log.warning("%s ('%s') sin generador; añádelo a GENERADORES", fid, nombre)
            continue
        ruta = salida / f"{fid}.png"
        cv2.imwrite(str(ruta), generador())
        escritas.append(ruta)
    log.info("%d plantillas vectoriales en %s", len(escritas), salida)
    return escritas
