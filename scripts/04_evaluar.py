"""
Evaluación out-of-fold: F1 por figura, QWK sobre el nivel, Bland-Altman sobre PD,
todo estratificado por tramo de edad. Guarda data/processed/evaluacion.json.
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold
from xgboost import XGBClassifier

from grafomotor.config import load_config
from grafomotor.evaluation import (
    bland_altman, estratificar_por_tramo, metricas_nivel, metricas_por_figura,
)
from grafomotor.io import cargar_etiquetas
from grafomotor.model.dataset import construir
from grafomotor.model.registry import cargar_modelo
from grafomotor.scoring.baremo import cargar_baremo, pd_a_percentil
from grafomotor.scoring.niveles import nivel_desde_percentil


def main() -> int:
    cfg = load_config()
    features = pd.read_parquet(cfg.ruta("processed") / "features.parquet")
    etiquetas = cargar_etiquetas(cfg.ruta("labels"))
    datos = construir(features, etiquetas)
    modelo, manifiesto = cargar_modelo(cfg.ruta("models") / "actual")
    baremo = cargar_baremo(cfg.ruta("baremos"))
    sco = cfg.get("scoring", default={})

    # predicciones out-of-fold para no evaluar sobre datos vistos
    y_oof = np.zeros_like(datos.y)
    for tr, te in GroupKFold(n_splits=cfg.get("modelo", "cv", "folds", default=5)).split(
        datos.X, datos.y, groups=datos.grupos
    ):
        m = XGBClassifier(**modelo.get_params())
        m.fit(datos.X[tr], datos.y[tr])
        y_oof[te] = m.predict(datos.X[te])

    fig_metrics = metricas_por_figura(datos.y, y_oof, datos.figura_id)
    estrat = estratificar_por_tramo(datos.y, y_oof, datos.figura_id, datos.edad_meses)

    # nivel: PD real vs PD predicho por niño
    dfp = pd.DataFrame({"child_id": datos.grupos, "edad": datos.edad_meses,
                        "y": datos.y, "yhat": y_oof})
    filas = []
    for cid, g in dfp.groupby("child_id"):
        edad = int(g["edad"].iloc[0])
        pc_real = pd_a_percentil(int(g["y"].sum()), edad, baremo)["percentil"]
        pc_pred = pd_a_percentil(int(g["yhat"].sum()), edad, baremo)["percentil"]
        n_cl = int(sco.get("n_clases", 2))
        filas.append({
            "child_id": cid, "PD_real": int(g["y"].sum()), "PD_pred": int(g["yhat"].sum()),
            "nivel_real": nivel_desde_percentil(pc_real, n_cl).nivel,
            "nivel_pred": nivel_desde_percentil(pc_pred, n_cl).nivel,
        })
    niv = pd.DataFrame(filas)
    etiquetas_nivel = (["Adecuado", "En riesgo"] if sco.get("n_clases", 2) == 2
                       else ["Adecuado", "Bajo", "Muy bajo"])

    salida = {
        "modelo": manifiesto,
        "por_figura": fig_metrics,
        "estratificado_por_tramo": estrat,
        "nivel": metricas_nivel(niv["nivel_real"], niv["nivel_pred"], etiquetas_nivel),
        "bland_altman_PD": bland_altman(niv["PD_real"], niv["PD_pred"]),
    }
    out = cfg.ruta("processed") / "evaluacion.json"
    out.write_text(json.dumps(salida, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(salida, indent=2, ensure_ascii=False))
    print(f"\n-> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
