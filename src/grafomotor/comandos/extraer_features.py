"""Paso 02 (modelo A): data/interim/ -> features.parquet (6 indicadores por figura)."""
from __future__ import annotations

import argparse

import pandas as pd

from grafomotor.artefactos import Artefactos
from grafomotor.config import Config
from grafomotor.features.extract import extraer_indicadores
from grafomotor.io import a_binaria, cargar_plantillas, leer_gris
from grafomotor.logs import obtener_logger

AYUDA = "modelo A: calcula los 6 indicadores geométricos -> data/processed/features.parquet"
log = obtener_logger(__name__)


def agregar_argumentos(p: argparse.ArgumentParser) -> None:
    pass


def ejecutar(args: argparse.Namespace, cfg: Config) -> int:
    plantillas = cargar_plantillas(cfg, estricto=False)
    filas = []
    for png in sorted(cfg.ruta("interim").glob("*__*.png")):
        child_id, fid = png.stem.split("__")
        if fid not in plantillas:
            continue
        figura = a_binaria(leer_gris(png))
        vec = extraer_indicadores(figura, plantillas[fid], fid, cfg.figuras.get(fid, {}))
        filas.append({"child_id": child_id, "figura_id": fid, **vec.valores,
                      **{f"raw_{k}": v for k, v in vec.raw.items()}})

    destino = Artefactos.de_config(cfg).features
    destino.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(filas).to_parquet(destino, index=False)
    log.info("%d figuras -> %s", len(filas), destino)
    return 0
