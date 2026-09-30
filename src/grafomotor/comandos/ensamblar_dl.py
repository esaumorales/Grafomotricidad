"""
Paso 14 (modelo B): ensamble de semillas + aumento en la prueba (TTA), SIN reentrenar.

Reutiliza los modelos por fold ya guardados de una variante y de sus semillas extra
(`<base>`, `<base>_s1`, `<base>_s2`, ...): cada niño del fold k se predice con el modelo
fold k de cada semilla (ninguno lo vio al entrenar) y se promedian las probabilidades.

  grafomotor ensamblar-dl --base resnet18_robusto            ensamble + TTA
  grafomotor ensamblar-dl --base resnet18_robusto --sin-tta  solo ensamble

Salida: una variante nueva `<base>_ens` (o `<base>_ens_sintta`) con su oof y evaluación,
que `comparar` y `resumen-variantes` tratan como cualquier otra.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd
import torch

from grafomotor.artefactos import Artefactos
from grafomotor.config import Config
from grafomotor.dl.entrenar import predecir
from grafomotor.dl.modelo import cargar
from grafomotor.dl.utilidades import dispositivo
from grafomotor.evaluation.reporte import evaluar_oof, resumen_corto
from grafomotor.io import guardar_json
from grafomotor.logs import obtener_logger
from grafomotor.scoring.baremo import cargar_baremo
from grafomotor.scoring.niveles import CriterioNiveles

AYUDA = "modelo B: ensamble de semillas + TTA con los modelos ya entrenados (sin reentrenar)"
log = obtener_logger(__name__)


def agregar_argumentos(p: argparse.ArgumentParser) -> None:
    p.add_argument("--base", required=True, help="variante base (p. ej. resnet18_robusto)")
    p.add_argument("--sin-tta", action="store_true", help="no aplicar aumento en la prueba")


def semillas_de(art: Artefactos, base: str) -> list[str]:
    """La variante base y sus semillas extra que tengan modelos por fold guardados."""
    extra = sorted(p.name for p in (art.modelos / "dl").glob(f"{base}_s*")
                   if p.name.removeprefix(f"{base}_s").isdigit())
    candidatas = [base, *extra]
    return [v for v in candidatas if any(art.dir_modelo_dl(v).glob("fold*.pt"))]


def ejecutar(args: argparse.Namespace, cfg: Config) -> int:
    art = Artefactos.de_config(cfg)
    variantes = semillas_de(art, args.base)
    if not variantes:
        log.error("no hay modelos por fold para %s en %s", args.base, art.modelos / "dl")
        return 1
    tta = not args.sin_tta
    figuras, disp = list(cfg.figuras), str(dispositivo())
    oof = pd.read_parquet(art.oof_dl(args.base))
    carpeta = art.carpeta_dl(art.lado_de_variante(args.base))
    prep = pd.read_csv(carpeta / "_preparacion_dl.csv")[["child_id", "figura_id", "dl_path"]]
    df = oof.merge(prep, on=["child_id", "figura_id"], how="left")
    log.info("ensamble de %d modelos por fold (%s) · TTA %s", len(variantes),
             ", ".join(variantes), "sí" if tta else "no")

    probs = []
    for v in variantes:
        p = pd.Series(np.nan, index=df.index)
        for k in sorted(df["fold"].unique()):
            prueba = df[(df["fold"] == k) & df["dl_path"].notna()]
            modelo, _ = cargar(art.modelo_dl_fold(v, int(k)), disp)
            p.loc[prueba.index] = predecir(modelo, prueba, carpeta, figuras, tta=tta)
            del modelo
        probs.append(p)
        if disp == "cuda":
            torch.cuda.empty_cache()

    prob = pd.concat(probs, axis=1).mean(axis=1, skipna=False)
    nombre = f"{args.base}_ens" + ("" if tta else "_sintta")
    salida = df[["child_id", "figura_id", "edad_meses", "fold", "y"]].assign(
        prob=prob, yhat=(prob >= 0.5).astype(float).where(prob.notna()), modelo=f"B_{nombre}")
    salida.to_parquet(art.oof_dl(nombre), index=False)

    rep = evaluar_oof(salida, cargar_baremo(cfg.ruta("baremos")),
                      CriterioNiveles.de_config(cfg))
    rep["modelo"] = {"variante": nombre, "ensamble_de": variantes, "tta": tta}
    guardar_json(rep, art.evaluacion_dl(nombre))
    print(json.dumps({"variante": nombre, **resumen_corto(rep)}, indent=2, ensure_ascii=False))
    return 0
