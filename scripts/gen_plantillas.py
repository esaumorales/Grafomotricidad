"""
Genera plantillas de referencia SINTÉTICAS para las 6 figuras de `config.yaml > figuras`.

>>> Son un MARCADOR DE POSICIÓN para poder ejecutar todo el pipeline sin datos reales.
>>> Sustitúyelas por las figuras oficiales de la Visopercepción (Vis) del CUMANIN-2
    (mismo nombre de archivo: data/templates/F01.png ...).

PNG binario, 512x512, trazo blanco (255) sobre fondo negro (0): igual que lo que
produce el preprocesamiento.
"""
from __future__ import annotations

import sys

import cv2
import numpy as np

from grafomotor.config import load_config

L = 512
M = 96          # margen
G = 5           # grosor de trazo


def _lienzo() -> np.ndarray:
    return np.zeros((L, L), np.uint8)


def circulo() -> np.ndarray:
    im = _lienzo()
    cv2.circle(im, (L // 2, L // 2), (L - 2 * M) // 2, 255, G)
    return im


def cuadrado() -> np.ndarray:
    im = _lienzo()
    cv2.rectangle(im, (M, M), (L - M, L - M), 255, G)
    return im


def triangulo() -> np.ndarray:
    im = _lienzo()
    p = np.array([[L // 2, M], [M, L - M], [L - M, L - M]], np.int32)
    cv2.polylines(im, [p], True, 255, G)
    return im


def rombo() -> np.ndarray:
    im = _lienzo()
    p = np.array([[L // 2, M], [L - M, L // 2], [L // 2, L - M], [M, L // 2]], np.int32)
    cv2.polylines(im, [p], True, 255, G)
    return im


def cruz() -> np.ndarray:
    im = _lienzo()
    cv2.line(im, (L // 2, M), (L // 2, L - M), 255, G)
    cv2.line(im, (M, L // 2), (L - M, L // 2), 255, G)
    return im


def cruz_oblicua() -> np.ndarray:
    im = _lienzo()
    cv2.line(im, (M, M), (L - M, L - M), 255, G)
    cv2.line(im, (L - M, M), (M, L - M), 255, G)
    return im


GEN = {
    "círculo": circulo, "cruz": cruz, "cuadrado": cuadrado, "triángulo": triangulo,
    "cruz oblicua": cruz_oblicua, "rombo": rombo,
}


def main() -> int:
    cfg = load_config()
    out = cfg.ruta("templates")
    out.mkdir(parents=True, exist_ok=True)
    for fid, meta in cfg.figuras.items():
        nombre = meta.get("nombre", "")
        gen = GEN.get(nombre)
        if gen is None:
            print(f"[SALTO] {fid} ('{nombre}') sin generador sintético; añádelo a mano.")
            continue
        cv2.imwrite(str(out / f"{fid}.png"), gen())
        print(f"[OK] {fid}.png  ({nombre})")
    print(f"\nPlantillas sintéticas en {out}  —  REEMPLAZAR por las reales del CUMANIN-2.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
