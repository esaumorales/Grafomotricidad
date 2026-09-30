"""
Paso 11: explicabilidad del modelo B con Grad-CAM sobre las figuras de prueba de cada fold.

Mide qué fracción del mapa cae sobre el trazo y cuál en el borde de la imagen: si la red
mira fuera del trazo (sombras, borde de la hoja) está usando un atajo, no los criterios.
Guarda un resumen y ejemplos superpuestos (para el artículo).
"""
from __future__ import annotations

import argparse
import json

import cv2
import numpy as np
import pandas as pd

from grafomotor.artefactos import Artefactos
from grafomotor.config import Config
from grafomotor.dl.gradcam import atencion_en_trazo, mapa_gradcam, superponer
from grafomotor.dl.modelo import cargar
from grafomotor.dl.utilidades import dispositivo
from grafomotor.io import guardar_json, leer_gris
from grafomotor.logs import obtener_logger

AYUDA = "Grad-CAM del modelo B: dónde mira la red y si usa atajos (bordes, sombras)"
log = obtener_logger(__name__)

UMBRAL_ALERTA_BORDE = 0.25   # >25 % del mapa en el borde de la imagen -> posible atajo
COLUMNAS = ["frac_en_trazo", "frac_area_trazo", "frac_en_borde"]


def agregar_argumentos(p: argparse.ArgumentParser) -> None:
    p.add_argument("--arq", default=None, help="variante de B")
    p.add_argument("--ejemplos", type=int, default=3, help="ejemplos guardados por figura")


def resumir(df: pd.DataFrame) -> dict:
    return {
        "n": len(df),
        "global": df[COLUMNAS].mean().round(3).to_dict(),
        # > 1: la red mira el trazo más de lo que ocuparía por azar
        "enriquecimiento_trazo": round(float(
            (df["frac_en_trazo"] / df["frac_area_trazo"].clip(lower=1e-3)).median()), 2),
        "por_figura": df.groupby("figura_id")[COLUMNAS].mean().round(3).to_dict(orient="index"),
        "por_acierto": df.groupby("acierto")[COLUMNAS].mean().round(3).to_dict(orient="index"),
        "alerta_atajo": (df.groupby("figura_id")["frac_en_borde"].mean()
                         .loc[lambda s: s > UMBRAL_ALERTA_BORDE].round(3).to_dict()),
    }


def ejecutar(args: argparse.Namespace, cfg: Config) -> int:
    art = Artefactos.de_config(cfg)
    variante = args.arq or cfg.get("dl", "arquitectura", default="resnet18")
    idx = {f: i for i, f in enumerate(cfg.figuras)}
    disp = str(dispositivo())

    oof = (pd.read_parquet(art.oof_dl(variante)).dropna(subset=["yhat"])
           .merge(pd.read_csv(art.preparacion_dl)[["child_id", "figura_id", "dl_path"]],
                  on=["child_id", "figura_id"]))
    carpeta_ej = art.dir_ejemplos_gradcam(variante)
    carpeta_ej.mkdir(parents=True, exist_ok=True)

    filas, guardados = [], dict.fromkeys(cfg.figuras, 0)
    for k, g in oof.groupby("fold"):
        modelo, _ = cargar(art.modelo_dl_fold(variante, int(k)), disp)
        for r in g.itertuples(index=False):
            img = leer_gris(art.interim_dl / r.dl_path)
            pred, esperado = int(r.yhat), int(r.y)
            cam = mapa_gradcam(modelo, img, idx[r.figura_id], clase=pred)  # explica lo predicho
            filas.append({"figura_id": r.figura_id, "child_id": r.child_id,
                          "acierto": int(pred == esperado), **atencion_en_trazo(cam, img)})
            if guardados[r.figura_id] < args.ejemplos:
                nombre = f"{r.figura_id}_{r.child_id}_pred{pred}_exp{esperado}.png"
                cv2.imwrite(str(carpeta_ej / nombre), superponer(img, cam))
                guardados[r.figura_id] += 1
        del modelo

    salida = resumir(pd.DataFrame(filas))
    guardar_json(salida, art.gradcam(variante))
    print(json.dumps({k: salida[k] for k in ("n", "global", "enriquecimiento_trazo",
                                             "alerta_atajo")}, indent=2, ensure_ascii=False))
    if salida["alerta_atajo"]:
        log.warning("posible atajo (mira el borde) en: %s", list(salida["alerta_atajo"]))
    log.info("-> %s · ejemplos en %s", art.gradcam(variante), carpeta_ej)
    return 0 if np.isfinite(salida["enriquecimiento_trazo"]) else 1
