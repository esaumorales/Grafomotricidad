"""Métricas de evaluación (Etapa 4 de la arquitectura)."""
from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    balanced_accuracy_score, cohen_kappa_score, confusion_matrix, f1_score,
)


def metricas_por_figura(y_true, y_pred, figura_id) -> dict:
    """F1 y exactitud balanceada por cada figura + global (macro)."""
    y_true, y_pred, figura_id = map(np.asarray, (y_true, y_pred, figura_id))
    out = {"global": {
        "f1_macro": round(f1_score(y_true, y_pred, average="macro"), 3),
        "balanced_acc": round(balanced_accuracy_score(y_true, y_pred), 3),
        "n": int(len(y_true)),
    }, "por_figura": {}}
    for fig in np.unique(figura_id):
        m = figura_id == fig
        if m.sum() < 2 or len(np.unique(y_true[m])) < 2:
            out["por_figura"][str(fig)] = {"n": int(m.sum()), "aviso": "pocos casos / una sola clase"}
            continue
        out["por_figura"][str(fig)] = {
            "f1_macro": round(f1_score(y_true[m], y_pred[m], average="macro"), 3),
            "balanced_acc": round(balanced_accuracy_score(y_true[m], y_pred[m]), 3),
            "n": int(m.sum()),
        }
    return out


def qwk(y_true, y_pred) -> float:
    """Kappa ponderado cuadrático (para el nivel ordinal o la puntuación total)."""
    return round(cohen_kappa_score(y_true, y_pred, weights="quadratic"), 3)


def metricas_nivel(nivel_true, nivel_pred, etiquetas: list[str]) -> dict:
    """Concordancia entre el nivel predicho y el del docente evaluador."""
    idx = {e: i for i, e in enumerate(etiquetas)}
    yt = [idx[v] for v in nivel_true]
    yp = [idx[v] for v in nivel_pred]
    return {
        "qwk": qwk(yt, yp),
        "kappa_lineal": round(cohen_kappa_score(yt, yp, weights="linear"), 3),
        "acuerdo_exacto": round(float(np.mean(np.array(yt) == np.array(yp))), 3),
        "f1_macro": round(f1_score(yt, yp, average="macro"), 3),
        "matriz_confusion": confusion_matrix(yt, yp, labels=list(range(len(etiquetas)))).tolist(),
        "etiquetas": etiquetas,
    }


def bland_altman(total_true, total_pred) -> dict:
    """Acuerdo sobre la puntuación total (PD) frente al docente: sesgo y límites."""
    a, b = np.asarray(total_true, float), np.asarray(total_pred, float)
    dif = b - a
    sesgo = float(np.mean(dif))
    sd = float(np.std(dif, ddof=1)) if len(dif) > 1 else 0.0
    return {
        "sesgo": round(sesgo, 2),
        "limite_inferior": round(sesgo - 1.96 * sd, 2),
        "limite_superior": round(sesgo + 1.96 * sd, 2),
        "sd_diferencias": round(sd, 2),
        "n": int(len(dif)),
    }
