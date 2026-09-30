"""
Paso 08 (modelo B): entrena la red con las MISMAS particiones por niño que el modelo A.

  grafomotor entrenar-dl                          resnet18 (config.yaml > dl)
  grafomotor entrenar-dl --arq efficientnet_b0
  grafomotor entrenar-dl --aumento robusto        variante "resnet18_robusto"
  grafomotor entrenar-dl --semillas 3             repite con 3 semillas (media ± DE)
  grafomotor entrenar-dl --final                  además, un modelo con todos los niños
  grafomotor entrenar-dl --rapido                 2+2 épocas, solo para probar la cadena

Salidas por variante V (nombres en grafomotor.artefactos): models/dl/V/fold<k>.pt,
historial.json, oof_dl_V.parquet, evaluacion_dl_V.json y, con --semillas,
variabilidad_dl_V.json.
"""
from __future__ import annotations

import argparse
import json
import time

import numpy as np
import pandas as pd
import torch

from grafomotor.artefactos import Artefactos, nombre_variante
from grafomotor.config import Config
from grafomotor.dl.aumentos import PERFILES
from grafomotor.dl.entrenar import CONFIG_POR_DEFECTO, entrenar_fold, predecir
from grafomotor.dl.modelo import ARQUITECTURAS, guardar
from grafomotor.dl.utilidades import dispositivo
from grafomotor.evaluation.particiones import folds_de, obtener_particiones
from grafomotor.evaluation.reporte import evaluar_oof, resumen_corto
from grafomotor.io import cargar_etiquetas, guardar_json
from grafomotor.logs import obtener_logger
from grafomotor.scoring.baremo import cargar_baremo

AYUDA = "modelo B: entrena la red (2 fases) por fold -> oof_dl_<variante>.parquet"
log = obtener_logger(__name__)


def agregar_argumentos(p: argparse.ArgumentParser) -> None:
    p.add_argument("--arq", choices=list(ARQUITECTURAS), default=None)
    p.add_argument("--aumento", choices=PERFILES, default=None)
    p.add_argument("--semillas", type=int, default=1, help="repeticiones con semillas distintas")
    p.add_argument("--final", action="store_true", help="entrenar también con todos los niños")
    p.add_argument("--rapido", action="store_true", help="2+2 épocas (solo para probar)")


def tabla_de_entrenamiento(cfg: Config, art: Artefactos) -> pd.DataFrame:
    """Etiquetas + recorte de cada figura + fold compartido."""
    etiquetas = cargar_etiquetas(cfg.ruta("labels"))
    particiones = obtener_particiones(art.particiones, etiquetas,
                                      int(cfg.get("comparacion", "folds", default=5)))
    prep = pd.read_csv(art.preparacion_dl)
    df = etiquetas.merge(prep[["child_id", "figura_id", "dl_path"]],
                         on=["child_id", "figura_id"], how="left")
    df["fold"] = folds_de(df["child_id"], particiones)
    return df


def entrenar_variante(cfg: Config, cfg_dl: dict, variante: str, df: pd.DataFrame,
                      final: bool) -> dict:
    """Entrena los K folds de una variante, guarda todo y devuelve el resumen de métricas."""
    art = Artefactos.de_config(cfg)
    figuras = list(cfg.figuras)
    medibles = df[df["dl_path"].notna()]
    disp = dispositivo()
    n_folds = int(df["fold"].nunique())
    log.info("variante %s · %s · aumento %s · semilla %s · %s · %d figuras · %d niños",
             variante, cfg_dl["arquitectura"], cfg_dl["aumento"], cfg_dl["semilla"], disp,
             len(medibles), df["child_id"].nunique())
    art.dir_modelo_dl(variante).mkdir(parents=True, exist_ok=True)

    prob = pd.Series(np.nan, index=df.index)
    historial, t0 = {}, time.perf_counter()
    for k in range(n_folds):
        log.info("fold %d/%d", k + 1, n_folds)
        prueba = medibles[medibles["fold"] == k]
        res = entrenar_fold(medibles[medibles["fold"] != k], art.interim_dl, figuras, cfg_dl, disp)
        prob.loc[prueba.index] = predecir(res.modelo, prueba, art.interim_dl, figuras)
        guardar(res.modelo, art.modelo_dl_fold(variante, k), {"fold": k, "cfg": cfg_dl})
        historial[f"fold{k}"] = {"mejor_epoca": res.mejor_epoca, "epocas": res.historial}
        del res
        if disp.type == "cuda":
            torch.cuda.empty_cache()
    segundos = round(time.perf_counter() - t0, 1)

    oof = df[["child_id", "figura_id", "edad_meses", "fold"]].assign(
        y=df["puntaje"], prob=prob, yhat=(prob >= 0.5).astype(float).where(prob.notna()),
        modelo=f"B_{variante}")
    oof.to_parquet(art.oof_dl(variante), index=False)
    guardar_json({"cfg": cfg_dl, "segundos_entrenamiento": segundos, **historial},
                 art.historial_dl(variante))

    rep = evaluar_oof(oof, cargar_baremo(cfg.ruta("baremos")),
                      int(cfg.get("scoring", "n_clases", default=2)))
    rep["modelo"] = {"variante": variante, "cfg": cfg_dl, "dispositivo": str(disp),
                     "segundos_entrenamiento_cv": segundos}
    guardar_json(rep, art.evaluacion_dl(variante))
    corto = resumen_corto(rep)
    print(json.dumps({"variante": variante, **corto}, indent=2, ensure_ascii=False))

    if final:
        log.info("modelo final con todos los niños")
        res = entrenar_fold(medibles, art.interim_dl, figuras, cfg_dl, disp)
        guardar(res.modelo, art.modelo_dl_final(variante), {"fold": "todos", "cfg": cfg_dl})
    return corto


def resumen_semillas(resultados: dict[str, dict]) -> dict:
    tabla = pd.DataFrame(resultados).T.astype(float)
    return {m: {"media": round(float(tabla[m].mean()), 3),
                "de": round(float(tabla[m].std(ddof=1)), 3)} for m in tabla.columns}


def ejecutar(args: argparse.Namespace, cfg: Config) -> int:
    art = Artefactos.de_config(cfg)
    cfg_dl = {**CONFIG_POR_DEFECTO, **dict(cfg.get("dl", default={}))}
    cfg_dl["arquitectura"] = args.arq or cfg_dl["arquitectura"]
    cfg_dl["aumento"] = args.aumento or cfg_dl["aumento"]
    if args.rapido:
        cfg_dl.update(epocas_fase1=2, epocas_fase2=2)
    df = tabla_de_entrenamiento(cfg, art)

    resultados = {}
    for i in range(args.semillas):
        variante = nombre_variante(cfg_dl["arquitectura"], cfg_dl["aumento"], i)
        cfg_i = {**cfg_dl, "semilla": int(cfg_dl["semilla"]) + i}
        resultados[variante] = entrenar_variante(cfg, cfg_i, variante, df,
                                                 final=args.final and i == 0)

    if args.semillas > 1:
        base = nombre_variante(cfg_dl["arquitectura"], cfg_dl["aumento"])
        resumen = resumen_semillas(resultados)
        guardar_json({"variante": base, "n_semillas": args.semillas, "resumen": resumen,
                      "por_semilla": resultados}, art.variabilidad_dl(base))
        print("\nvariabilidad entre semillas (media ± DE):")
        for m, v in resumen.items():
            print(f"  {m:24s} {v['media']:.3f} ± {v['de']:.3f}")
    return 0
