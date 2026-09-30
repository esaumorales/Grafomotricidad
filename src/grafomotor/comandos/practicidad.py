"""
Paso 12: practicidad de A y B: pasos, segundos por hoja (15 figuras, de la foto a la
puntuación, sin explicaciones) y tasa de fallos out-of-fold.

Para medir tiempos limpios no debe haber otro proceso pesado corriendo a la vez.
"""
from __future__ import annotations

import argparse
import json
import time

import numpy as np
import pandas as pd

from grafomotor.artefactos import Artefactos
from grafomotor.config import Config
from grafomotor.dl.utilidades import dispositivo
from grafomotor.io import cargar_etiquetas, guardar_json, leer_gris, ruta_foto
from grafomotor.logs import obtener_logger
from grafomotor.model.registry import cargar_modelo
from grafomotor.predictores import PredictorA, PredictorB

AYUDA = "practicidad de A y B: pasos, segundos por hoja y tasa de fallos"
log = obtener_logger(__name__)

PASOS = {
    "A": ["corregir perspectiva", "normalizar iluminación", "binarizar", "aislar el trazo",
          "registrar contra la plantilla", "calcular 6 indicadores", "XGBoost", "SHAP"],
    "B": ["corregir perspectiva", "recortar la figura (224×224)", "red profunda", "Grad-CAM"],
}


def agregar_argumentos(p: argparse.ArgumentParser) -> None:
    p.add_argument("--arq", default=None, help="variante de B")
    p.add_argument("--hojas", type=int, default=20, help="hojas (niños) cronometradas")


def _tasa_fallos(ruta) -> float | None:
    return round(float(pd.read_parquet(ruta)["yhat"].isna().mean()), 4) if ruta.exists() else None


def ejecutar(args: argparse.Namespace, cfg: Config) -> int:
    art = Artefactos.de_config(cfg)
    variante = args.arq or cfg.get("dl", "arquitectura", default="resnet18")
    etiquetas = cargar_etiquetas(cfg.ruta("labels"))
    ninos = sorted(etiquetas["child_id"].unique())[: args.hojas]

    predictores = {
        "A": PredictorA(cfg, {"final": cargar_modelo(art.dir_modelo_ml)[0]}),
        "B": PredictorB.desde_variante(cfg, variante, "final"),
    }
    blanco = np.full((224, 224), 255, np.uint8)
    predictores["B"].predecir_lote([blanco], [next(iter(cfg.figuras))], "final")  # calentar GPU

    tiempos: dict[str, list[float]] = {"A": [], "B": []}
    for nino in ninos:
        hoja = etiquetas[etiquetas["child_id"] == nino]
        rutas = [ruta_foto(cfg, p) for p in hoja["imagen_path"]]
        for m, pred in predictores.items():
            t0 = time.perf_counter()
            grises = [leer_gris(r) for r in rutas]      # la lectura cuenta: es parte del uso real
            pred.predecir_lote(grises, list(hoja["figura_id"]), "final")
            tiempos[m].append(time.perf_counter() - t0)

    oof = {"A": art.oof_ml, "B": art.oof_dl(variante)}
    salida = {
        "variante_B": variante, "hojas_medidas": len(ninos), "dispositivo_B": str(dispositivo()),
        **{m: {"pasos": PASOS[m], "n_pasos": len(PASOS[m]),
               "seg_por_hoja_media": round(float(np.mean(t)), 2),
               "seg_por_hoja_de": round(float(np.std(t, ddof=1)), 2) if len(t) > 1 else 0.0,
               "tasa_fallos_oof": _tasa_fallos(oof[m])} for m, t in tiempos.items()},
        "nota": "tiempos sin explicaciones (SHAP / Grad-CAM); la GPU solo acelera a B",
    }
    guardar_json(salida, art.practicidad(variante))
    print(json.dumps(salida, indent=2, ensure_ascii=False))
    return 0
