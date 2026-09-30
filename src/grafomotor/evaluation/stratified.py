"""Reportes estratificados: por edad en años (3, 4, 5) y por tramo de la Tabla B.9."""
from __future__ import annotations

import numpy as np

from grafomotor.evaluation.metrics import metricas_binarias
from grafomotor.scoring.baremo import tramo_de_edad


def edad_en_anios(edad_meses) -> np.ndarray:
    return np.asarray(edad_meses, int) // 12


def estratificar_por_edad(y_true, y_pred, edad_meses) -> dict:
    """Métricas por figura (0/1) separadas por 3, 4 y 5 años."""
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    anios = edad_en_anios(edad_meses)
    return {f"{a}_anios": metricas_binarias(y_true[anios == a], y_pred[anios == a])
            for a in sorted(set(anios))}


def estratificar_por_tramo(y_true, y_pred, figura_id, edad_meses) -> dict:
    """Métricas por tramo de edad de la Tabla B.9 (ojo: efecto suelo a los 3 años)."""
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    tramos = np.array([tramo_de_edad(int(e)) for e in edad_meses])
    return {tr: metricas_binarias(y_true[tramos == tr], y_pred[tramos == tr])
            for tr in sorted(set(tramos))}
