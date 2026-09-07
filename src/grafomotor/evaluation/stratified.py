"""Reporte estratificado por tramo de edad de 4 meses (3;0–5;11)."""
from __future__ import annotations

import numpy as np

from grafomotor.evaluation.metrics import metricas_por_figura
from grafomotor.scoring.baremo import tramo_de_edad


def estratificar_por_tramo(y_true, y_pred, figura_id, edad_meses) -> dict:
    y_true, y_pred, figura_id, edad_meses = map(np.asarray, (y_true, y_pred, figura_id, edad_meses))
    tramos = np.array([tramo_de_edad(int(e)) for e in edad_meses])
    out = {}
    for tr in sorted(set(tramos)):
        m = tramos == tr
        out[tr] = metricas_por_figura(y_true[m], y_pred[m], figura_id[m])["global"]
        out[tr]["tasa_acierto_real"] = round(float(y_true[m].mean()), 3)  # ojo efecto suelo a los 3
    return out
