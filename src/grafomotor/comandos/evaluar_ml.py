"""
Paso 04 (modelo A): predicciones out-of-fold con las particiones COMPARTIDAS con B.

Salidas: oof_ml.parquet (entrada de `comparar`) y evaluacion_ml.json.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from grafomotor.artefactos import Artefactos
from grafomotor.config import Config
from grafomotor.evaluation.particiones import folds_de, obtener_particiones
from grafomotor.evaluation.reporte import evaluar_oof, resumen_corto
from grafomotor.io import cargar_etiquetas, guardar_json
from grafomotor.logs import obtener_logger
from grafomotor.model.registry import cargar_modelo
from grafomotor.predictores import modelos_ml_por_fold
from grafomotor.scoring.baremo import cargar_baremo

AYUDA = "modelo A: evaluación out-of-fold ANIDADA con las particiones compartidas"
log = obtener_logger(__name__)


def predicciones_oof(cfg: Config, etiquetas: pd.DataFrame, particiones: pd.DataFrame
                     ) -> tuple[pd.DataFrame, dict[int, object]]:
    """Predicciones out-of-fold (validación anidada) y los hiperparámetros de cada fold.

    Figuras sin indicadores quedan como fallo (yhat = NaN).
    """
    modelos, datos, params = modelos_ml_por_fold(cfg, etiquetas, particiones)
    fold = folds_de(datos.grupos, particiones)
    prob = np.full(len(datos.y), np.nan)
    for k, m in modelos.items():
        prob[fold == k] = m.predict_proba(datos.X[fold == k])[:, 1]

    medidas = pd.DataFrame({"child_id": datos.grupos, "figura_id": datos.figura_id,
                            "prob": prob, "yhat": (prob >= 0.5).astype(float)})
    oof = (etiquetas[["child_id", "figura_id", "edad_meses", "puntaje"]]
           .rename(columns={"puntaje": "y"})
           .merge(medidas, on=["child_id", "figura_id"], how="left"))
    oof["fold"] = folds_de(oof["child_id"], particiones)
    oof["modelo"] = "A_xgboost"
    return oof, params


def agregar_argumentos(p: argparse.ArgumentParser) -> None:
    pass


def ejecutar(args: argparse.Namespace, cfg: Config) -> int:
    art = Artefactos.de_config(cfg)
    etiquetas = cargar_etiquetas(cfg.ruta("labels"))
    particiones = obtener_particiones(art.particiones, etiquetas,
                                      int(cfg.get("comparacion", "folds", default=5)))
    log.info("validación anidada: Grid Search dentro de cada fold (tarda unos minutos)")
    oof, params = predicciones_oof(cfg, etiquetas, particiones)
    oof.to_parquet(art.oof_ml, index=False)

    rep = evaluar_oof(oof, cargar_baremo(cfg.ruta("baremos")),
                      int(cfg.get("scoring", "n_clases", default=2)))
    rep["modelo"] = cargar_modelo(art.dir_modelo_ml)[1]
    rep["validacion"] = {"anidada": bool(cfg.get("modelo", "cv", "anidada", default=True)),
                         "hiperparametros_por_fold": params}
    guardar_json(rep, art.evaluacion_ml)
    print(json.dumps(resumen_corto(rep), indent=2, ensure_ascii=False))
    log.info("-> %s · %s", art.evaluacion_ml, art.oof_ml)
    return 0
