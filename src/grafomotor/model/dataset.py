"""Construye (X, y, grupos) a partir de features + etiquetas."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from grafomotor import ORDEN


@dataclass
class Datos:
    X: np.ndarray            # (n, 6) indicadores normalizados
    y: np.ndarray            # (n,)  0/1 puntaje de la figura
    grupos: np.ndarray       # (n,)  child_id  -> para CV agrupada por niño
    figura_id: np.ndarray    # (n,)  para métricas por figura
    edad_meses: np.ndarray   # (n,)  para estratificar
    feature_names: list[str]


def construir(features: pd.DataFrame, etiquetas: pd.DataFrame) -> Datos:
    """
    features:  columnas = child_id, figura_id, + los 6 indicadores (+ raw_*).
    etiquetas: columnas = child_id, figura_id, edad_meses, puntaje.
    """
    df = features.merge(
        etiquetas[["child_id", "figura_id", "edad_meses", "puntaje"]],
        on=["child_id", "figura_id"], how="inner", validate="one_to_one",
    )
    faltan = [c for c in ORDEN if c not in df.columns]
    if faltan:
        raise ValueError(f"Features sin columnas de indicadores: {faltan}")

    return Datos(
        X=df[ORDEN].to_numpy(dtype=float),
        y=df["puntaje"].to_numpy(dtype=int),
        grupos=df["child_id"].to_numpy(),
        figura_id=df["figura_id"].to_numpy(),
        edad_meses=df["edad_meses"].to_numpy(dtype=int),
        feature_names=list(ORDEN),
    )
