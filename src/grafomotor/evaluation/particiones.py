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


CRITERIOS = ("nino", "colegio")


def crear_particiones(etiquetas: pd.DataFrame, n_folds: int = 5, semilla: int = SEMILLA,
                      por: str = "nino") -> pd.DataFrame:
    """DataFrame (child_id, fold, criterio). Todas las figuras de un niño en el mismo fold.

    por="nino":    StratifiedGroupKFold por niño (validación interna).
    por="colegio": un fold por colegio (validación EXTERNA: se entrena con los demás
                   colegios y se prueba con uno que el modelo nunca vio).
    """
    if por not in CRITERIOS:
        raise ValueError(f"criterio de partición desconocido: {por} (usa {CRITERIOS})")
    if por == "colegio":
        if "colegio" not in etiquetas.columns:
            raise ValueError("para validar por colegio, etiquetas.csv necesita la columna "
                             "'colegio'")
        por_nino = etiquetas.drop_duplicates("child_id")[["child_id", "colegio"]]
        if etiquetas.groupby("child_id")["colegio"].nunique().gt(1).any():
            raise ValueError("hay niños asignados a más de un colegio en etiquetas.csv")
        colegios = sorted(por_nino["colegio"].unique())
        if len(colegios) < 2:
            raise ValueError("la validación por colegio necesita al menos 2 colegios")
        codigo = {c: k for k, c in enumerate(colegios)}
        df = por_nino.assign(fold=por_nino["colegio"].map(codigo))[["child_id", "fold"]]
    else:
        sgkf = StratifiedGroupKFold(n_splits=n_folds, shuffle=True, random_state=semilla)
        fold = pd.Series(-1, index=etiquetas.index)
        for k, (_, te) in enumerate(sgkf.split(etiquetas, etiquetas["puntaje"],
                                               groups=etiquetas["child_id"])):
            fold.iloc[te] = k
        df = pd.DataFrame({"child_id": etiquetas["child_id"], "fold": fold}
                          ).drop_duplicates("child_id")
    df = df.sort_values("child_id").reset_index(drop=True).assign(criterio=por)
    if df["child_id"].duplicated().any():
        raise RuntimeError("un niño quedó en más de un fold")
    return df


def obtener_particiones(ruta: str | Path, etiquetas: pd.DataFrame, n_folds: int = 5,
                        regenerar: bool = False, por: str = "nino") -> pd.DataFrame:
    """Lee particiones.csv; lo (re)crea si no existe, no cubre a todos los niños o se
    generó con otro criterio (niño / colegio)."""
    ruta = Path(ruta)
    if ruta.exists() and not regenerar:
        df = pd.read_csv(ruta)
        faltan = set(etiquetas["child_id"]) - set(df["child_id"])
        criterio = df["criterio"].iloc[0] if "criterio" in df.columns else "nino"
        folds_ok = por == "colegio" or df["fold"].nunique() == n_folds
        if not faltan and folds_ok and criterio == por:
            return df
        log.warning("particiones.csv desactualizado (%d niños sin fold, criterio %s -> %s): "
                    "se regenera", len(faltan), criterio, por)
    df = crear_particiones(etiquetas, n_folds, por=por)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta, index=False)
    return df


def particiones_de_config(cfg, etiquetas: pd.DataFrame) -> pd.DataFrame:
    """Particiones compartidas según config.yaml > comparacion (folds y criterio)."""
    from grafomotor.artefactos import Artefactos

    return obtener_particiones(Artefactos.de_config(cfg).particiones, etiquetas,
                               int(cfg.get("comparacion", "folds", default=5)),
                               por=cfg.get("comparacion", "agrupar_por", default="nino"))


def folds_de(child_ids, particiones: pd.DataFrame) -> np.ndarray:
    mapa = dict(zip(particiones["child_id"], particiones["fold"], strict=True))
    return np.array([mapa[c] for c in child_ids])
