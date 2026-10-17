"""Construye (X, y, grupos) a partir de features + etiquetas."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from grafomotor import ORDEN
from grafomotor.model.columnas import PREFIJO_FIGURA


@dataclass
class Datos:
    X: np.ndarray            # (n, k) columnas de entrada (ver model/columnas.py)
    y: np.ndarray            # (n,)  0/1 puntaje de la figura
    grupos: np.ndarray       # (n,)  child_id  -> para CV agrupada por niño
    figura_id: np.ndarray    # (n,)  para métricas por figura
    edad_meses: np.ndarray   # (n,)  para estratificar
    feature_names: list[str]


def matriz(df: pd.DataFrame, nombres: list[str]) -> np.ndarray:
    """Matriz de entrada desde una tabla con figura_id, los indicadores y las raw_*."""
    cols = []
    for n in nombres:
        if n.startswith(PREFIJO_FIGURA):
            cols.append((df["figura_id"] == n[len(PREFIJO_FIGURA):]).to_numpy(dtype=float))
        else:
            cols.append(df[n].to_numpy(dtype=float))
    X = np.column_stack(cols)
    X[np.isinf(X)] = np.nan          # igual que columnas.a_finito: infinito = faltante
    return X


def construir(features: pd.DataFrame, etiquetas: pd.DataFrame,
              nombres: list[str] | None = None) -> Datos:
    """
    features:  columnas = child_id, figura_id, + los 6 indicadores (+ raw_*).
    etiquetas: columnas = child_id, figura_id, edad_meses, puntaje.
    nombres:   columnas de entrada (`model.columnas.nombres_columnas`); por defecto, los 6.
    """
    nombres = list(nombres or ORDEN)
    df = features.merge(
        etiquetas[["child_id", "figura_id", "edad_meses", "puntaje"]],
        on=["child_id", "figura_id"], how="inner", validate="one_to_one",
    )
    faltan = [c for c in nombres if not c.startswith(PREFIJO_FIGURA) and c not in df.columns]
    if faltan:
        raise ValueError(f"Features sin columnas de entrada: {faltan}")

    return Datos(
        X=matriz(df, nombres),
        y=df["puntaje"].to_numpy(dtype=int),
        grupos=df["child_id"].to_numpy(),
        figura_id=df["figura_id"].to_numpy(),
        edad_meses=df["edad_meses"].to_numpy(dtype=int),
        feature_names=nombres,
    )
