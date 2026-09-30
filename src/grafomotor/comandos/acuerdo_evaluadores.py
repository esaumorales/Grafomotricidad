"""
Paso 16: acuerdo ENTRE EVALUADORES (el "techo humano").

CLAIM 2024 exige reportar la variabilidad entre evaluadores del estándar de referencia.
Además da el techo realista: un modelo no puede concordar con el experto más de lo que
dos expertos concuerdan entre sí.

Requiere data/labels/doble_calificacion.csv con la calificación INDEPENDIENTE de un
segundo evaluador sobre una parte de las hojas (se recomienda >= 20 % de los niños):

    child_id, figura_id, puntaje          (0/1, sin ver la del primer evaluador)

Mismas métricas que los modelos: kappa de Cohen por figura, CCI y Bland-Altman de la PD
y kappa ponderado del nivel. Salida: data/processed/acuerdo_evaluadores.json
"""
from __future__ import annotations

import argparse
import json

import pandas as pd

from grafomotor.artefactos import Artefactos
from grafomotor.config import Config
from grafomotor.evaluation.reporte import evaluar_oof, resumen_corto
from grafomotor.io import cargar_etiquetas, guardar_json
from grafomotor.logs import obtener_logger
from grafomotor.scoring.baremo import cargar_baremo
from grafomotor.scoring.niveles import CriterioNiveles

AYUDA = "acuerdo entre dos evaluadores expertos (techo humano de la concordancia)"
log = obtener_logger(__name__)


def agregar_argumentos(p: argparse.ArgumentParser) -> None:
    pass


def tabla_acuerdo(etiquetas: pd.DataFrame, segunda: pd.DataFrame) -> pd.DataFrame:
    """Formato OOF para reutilizar las métricas: y = evaluador 1, yhat = evaluador 2."""
    faltan = {"child_id", "figura_id", "puntaje"} - set(segunda.columns)
    if faltan:
        raise ValueError(f"doble_calificacion.csv sin columnas {sorted(faltan)}")
    if not segunda["puntaje"].isin([0, 1]).all():
        raise ValueError("doble_calificacion.csv: 'puntaje' debe ser 0 o 1")
    df = etiquetas[["child_id", "figura_id", "edad_meses", "puntaje"]].merge(
        segunda[["child_id", "figura_id", "puntaje"]], on=["child_id", "figura_id"],
        suffixes=("", "_2"), validate="one_to_one")
    return df.rename(columns={"puntaje": "y"}).assign(
        yhat=df["puntaje_2"].astype(float), prob=df["puntaje_2"].astype(float), fold=0
    ).drop(columns="puntaje_2")


def ejecutar(args: argparse.Namespace, cfg: Config) -> int:
    ruta = cfg.ruta("doble_calificacion")
    if not ruta.exists():
        log.error("falta %s: que un segundo evaluador califique por su cuenta al menos el "
                  "20 %% de las hojas (ver docs/DATOS.md)", ruta)
        return 1
    etiquetas = cargar_etiquetas(cfg.ruta("labels"))
    df = tabla_acuerdo(etiquetas, pd.read_csv(ruta))
    n_ninos, total = df["child_id"].nunique(), etiquetas["child_id"].nunique()

    rep = evaluar_oof(df, cargar_baremo(cfg.ruta("baremos")),
                      CriterioNiveles.de_config(cfg))
    rep["cobertura"] = {"ninos": n_ninos, "de": total, "fraccion": round(n_ninos / total, 3)}
    guardar_json(rep, Artefactos.de_config(cfg).acuerdo_evaluadores)
    corto = {k: v for k, v in resumen_corto(rep).items() if k != "tasa_fallos"}
    print(json.dumps({"cobertura": rep["cobertura"], **corto}, indent=2, ensure_ascii=False))
    if n_ninos / total < 0.2:
        log.warning("solo %.0f %% de los niños tiene doble calificación (se recomienda >= 20 %%)",
                    100 * n_ninos / total)
    return 0
