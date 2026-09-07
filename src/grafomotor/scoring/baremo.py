"""
Baremo del CUMANIN-2 (Visopercepción): PD -> T por tramo de edad de 4 meses.

El manual (pág. 89) define 12 baremos, 3 por año, de 3;0 a 6;11. El estudio usa
los 9 primeros (3;0 a 5;11). La tabla real se descarga de teacorrige.com; aquí se
carga desde un CSV (ver config/baremos_ejemplo.csv) y se anota la versión usada.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# límites inferiores (en meses) de cada tramo de 4 meses
_LIM = list(range(36, 72, 4))  # 36,40,44,48,52,56,60,64,68  -> hasta 5;11


def tramo_de_edad(edad_meses: int) -> str:
    """Devuelve el tramo tipo '4;0_4;3' para una edad en meses."""
    if not 36 <= edad_meses <= 71:
        raise ValueError(f"edad_meses={edad_meses} fuera de 3;0–5;11 (36–71)")
    base = max(m for m in _LIM if m <= edad_meses)
    a0, m0 = divmod(base, 12)
    a1, m1 = divmod(base + 3, 12)
    return f"{a0};{m0}_{a1};{m1}"


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
