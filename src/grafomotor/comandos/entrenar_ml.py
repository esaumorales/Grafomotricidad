"""Paso 03 (modelo A): XGBoost por figura con Grid Search y CV agrupada por niño."""
from __future__ import annotations

import argparse
import json

import pandas as pd

from grafomotor.artefactos import Artefactos
from grafomotor.config import Config
from grafomotor.io import cargar_etiquetas
from grafomotor.logs import obtener_logger
from grafomotor.model.dataset import construir
from grafomotor.model.registry import guardar_modelo, nuevo_manifiesto
from grafomotor.model.train import entrenar

AYUDA = "modelo A: entrena XGBoost (Grid Search, CV agrupada por niño) -> models/actual/"
log = obtener_logger(__name__)


def agregar_argumentos(p: argparse.ArgumentParser) -> None:
    pass


def ejecutar(args: argparse.Namespace, cfg: Config) -> int:
    art = Artefactos.de_config(cfg)
    datos = construir(pd.read_parquet(art.features), cargar_etiquetas(cfg.ruta("labels")))
    log.info("%d figuras · %d niños · tasa de acierto %.3f",
             len(datos.y), len(set(datos.grupos)), datos.y.mean())

    res = entrenar(datos, cfg.get("modelo", default={}))
    log.info("mejores hiperparámetros: %s", json.dumps(res.mejores_params))
    log.info("F1 macro (CV agrupada por niño): %.3f · por fold %s",
             res.cv_f1_macro, res.cv_f1_por_fold)
    guardar_modelo(res.modelo, nuevo_manifiesto(res, cfg), art.dir_modelo_ml)
    log.info("modelo -> %s", art.dir_modelo_ml)
    return 0
