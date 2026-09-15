"""
Baremo del CUMANIN (Visopercepción): PD -> Pc por tramo de edad.

Tramos y tabla: Tabla B.9 "Escala de Visopercepción" del manual CUMANIN original
(Portellano Pérez, Mateos Mateos y Martínez Arias), pág. 83. Esa tabla publica el
percentil (Pc) directo por tramo de edad EN MESES — no publica una puntuación T
para esta subescala. El estudio usa los tramos dentro de 3;0-5;11 (36-71 meses);
el tramo 67-78 del manual llega hasta 6;6, pero solo 67-71 cae dentro del alcance.

La columna "T" del CSV (si está) es una ESTIMACIÓN matemática a partir del Pc
(T = 50 + 10*Φ⁻¹(Pc/100), asumiendo distribución normal), no un valor publicado
en esta tabla — usarla con cautela, ver docs/DATOS.md.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# tramos reales de la Tabla B.9 (límite inferior, límite superior, etiqueta)
_TRAMOS = [
    (36, 42, "36_42"),
    (43, 48, "43_48"),
    (49, 54, "49_54"),
    (55, 60, "55_60"),
    (61, 66, "61_66"),
    (67, 78, "67_78"),
]


def tramo_de_edad(edad_meses: int) -> str:
    """Devuelve la etiqueta de tramo (p.ej. '49_54') de la Tabla B.9 para una edad en meses."""
    if not 36 <= edad_meses <= 71:
        raise ValueError(f"edad_meses={edad_meses} fuera de 3;0–5;11 (36–71)")
    for lo, hi, label in _TRAMOS:
        if lo <= edad_meses <= hi:
            return label
    raise ValueError(f"edad_meses={edad_meses} no cae en ningún tramo de la Tabla B.9")


def cargar_baremo(path: str | Path) -> pd.DataFrame:
    """CSV con columnas: tramo_edad, pd, T, percentil. Ignora líneas '#'."""
    df = pd.read_csv(path, comment="#")
    faltan = {"tramo_edad", "pd", "T"} - set(df.columns)
    if faltan:
        raise ValueError(f"Baremo sin columnas: {faltan}")
    return df


def pd_a_T(pd_valor: int, edad_meses: int, baremo: pd.DataFrame) -> dict:
    """Convierte una Puntuación Directa en T y percentil usando el tramo de la edad."""
    tramo = tramo_de_edad(edad_meses)
    sub = baremo[baremo["tramo_edad"] == tramo].sort_values("pd")
    if sub.empty:
        raise KeyError(f"El baremo no tiene el tramo '{tramo}'. Añádelo desde teacorrige.com.")
    # interpolación lineal por si falta ese PD exacto
    T = float(np.interp(pd_valor, sub["pd"], sub["T"]))
    pc = float(np.interp(pd_valor, sub["pd"], sub["percentil"])) if "percentil" in sub else float("nan")
    return {"tramo": tramo, "PD": int(pd_valor), "T": round(T, 1), "percentil": round(pc, 1)}
