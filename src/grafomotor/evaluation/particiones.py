"""
Particiones COMPARTIDAS por los dos modelos (regla de comparación justa).

Se asigna un fold a cada niño con StratifiedGroupKFold (grupo = child_id,
estratificado por el puntaje de la figura) y se guarda en
data/processed/particiones.csv. Tanto XGBoost como la ResNet leen ese archivo:
mismos niños, mismas etiquetas, mismo fold de prueba.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from grafomotor.logs import obtener_logger

log = obtener_logger(__name__)

SEMILLA = 20260930


def crear_particiones(etiquetas: pd.DataFrame, n_folds: int = 5,
                      semilla: int = SEMILLA) -> pd.DataFrame:
    """Devuelve un DataFrame (child_id, fold). Todas las figuras de un niño en el mismo fold."""
    sgkf = StratifiedGroupKFold(n_splits=n_folds, shuffle=True, random_state=semilla)
    fold = pd.Series(-1, index=etiquetas.index)
    for k, (_, te) in enumerate(sgkf.split(etiquetas, etiquetas["puntaje"],
                                           groups=etiquetas["child_id"])):
        fold.iloc[te] = k
    df = (pd.DataFrame({"child_id": etiquetas["child_id"], "fold": fold})
          .drop_duplicates("child_id").sort_values("child_id").reset_index(drop=True))
    if df["child_id"].duplicated().any():
        raise RuntimeError("un niño quedó en más de un fold")
    return df


def obtener_particiones(ruta: str | Path, etiquetas: pd.DataFrame, n_folds: int = 5,
                        regenerar: bool = False) -> pd.DataFrame:
    """Lee particiones.csv; si no existe (o no cubre a todos los niños), lo crea."""
    ruta = Path(ruta)
    if ruta.exists() and not regenerar:
        df = pd.read_csv(ruta)
        faltan = set(etiquetas["child_id"]) - set(df["child_id"])
        if not faltan and df["fold"].nunique() == n_folds:
            return df
        log.warning("particiones.csv desactualizado (%d niños sin fold): se regenera", len(faltan))
    df = crear_particiones(etiquetas, n_folds)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta, index=False)
    return df


def folds_de(child_ids, particiones: pd.DataFrame) -> np.ndarray:
    mapa = dict(zip(particiones["child_id"], particiones["fold"], strict=True))
    return np.array([mapa[c] for c in child_ids])
