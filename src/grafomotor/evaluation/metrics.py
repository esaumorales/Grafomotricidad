"""
Métricas de evaluación, comunes a los dos modelos (A: indicadores + XGBoost,
B: ResNet-18). Siguen las reglas de comparación justa del diseño ML vs DL:

  - por figura (0/1):  exactitud balanceada, F1 macro, sensibilidad, especificidad
                       y kappa de Cohen SIN ponderar (la puntuación es binaria)
  - PD total:          CCI (acuerdo absoluto) y Bland-Altman
  - nivel global:      kappa ponderado (ordinal)
"""
from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
)


def _r(x: float, nd: int = 3) -> float:
    return round(float(x), nd) if np.isfinite(x) else float("nan")


def metricas_binarias(y_true, y_pred) -> dict:
    """Métricas de una tarea 0/1 (1 = figura correcta)."""
    y_true, y_pred = np.asarray(y_true, int), np.asarray(y_pred, int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    sens = tp / (tp + fn) if (tp + fn) else float("nan")
    esp = tn / (tn + fp) if (tn + fp) else float("nan")
    una_clase = len(np.unique(y_true)) < 2
    out = {
        "n": len(y_true),
        "exactitud": _r(np.mean(y_true == y_pred)),
        "exactitud_balanceada": _r(np.nanmean([sens, esp])),
        "f1_macro": _r(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "sensibilidad": _r(sens),
        "especificidad": _r(esp),
        "kappa": (float("nan") if una_clase and len(np.unique(y_pred)) < 2
                  else _r(cohen_kappa_score(y_true, y_pred))),
        "tasa_acierto_real": _r(y_true.mean()),
    }
    if una_clase:
        out["aviso"] = "una sola clase en el criterio experto"
    return out


def metricas_por_figura(y_true, y_pred, figura_id) -> dict:
    """Métricas binarias globales y por cada figura."""
    y_true, y_pred, figura_id = map(np.asarray, (y_true, y_pred, figura_id))
    out = {"global": metricas_binarias(y_true, y_pred), "por_figura": {}}
    for fig in sorted(np.unique(figura_id)):
        m = figura_id == fig
        out["por_figura"][str(fig)] = metricas_binarias(y_true[m], y_pred[m])
    return out


def kappa_ponderado(y_true, y_pred, pesos: str = "quadratic") -> float:
    """Kappa ponderado (para el nivel ordinal)."""
    return _r(cohen_kappa_score(y_true, y_pred, weights=pesos))


# se mantiene el nombre anterior por compatibilidad
def qwk(y_true, y_pred) -> float:
    return kappa_ponderado(y_true, y_pred, "quadratic")


def metricas_nivel(nivel_true, nivel_pred, etiquetas: list[str]) -> dict:
    """Concordancia entre el nivel predicho y el del evaluador experto."""
    idx = {e: i for i, e in enumerate(etiquetas)}
    yt = [idx[v] for v in nivel_true]
    yp = [idx[v] for v in nivel_pred]
    return {
        "kappa_ponderado_cuadratico": kappa_ponderado(yt, yp, "quadratic"),
        "kappa_ponderado_lineal": kappa_ponderado(yt, yp, "linear"),
        "acuerdo_exacto": _r(np.mean(np.array(yt) == np.array(yp))),
        "f1_macro": _r(f1_score(yt, yp, average="macro", zero_division=0)),
        "matriz_confusion": confusion_matrix(yt, yp, labels=list(range(len(etiquetas)))).tolist(),
        "etiquetas": etiquetas,
    }


def icc_acuerdo_absoluto(*evaluadores) -> float:
    """CCI(A,1) de McGraw y Wong (1996) = ICC(2,1) de Shrout y Fleiss (1979).

    Un vector por evaluador (aquí: experto y modelo), un valor por niño. Mide acuerdo
    absoluto: penaliza tanto la falta de correlación como un sesgo sistemático.
    """
    x = np.column_stack([np.asarray(v, float) for v in evaluadores])
    n, k = x.shape
    if n < 2:
        return float("nan")
    media = x.mean()
    ss_filas = k * np.sum((x.mean(axis=1) - media) ** 2)
    ss_cols = n * np.sum((x.mean(axis=0) - media) ** 2)
    ss_total = np.sum((x - media) ** 2)
    ss_err = ss_total - ss_filas - ss_cols
    msr = ss_filas / (n - 1)
    msc = ss_cols / (k - 1)
    mse = ss_err / ((n - 1) * (k - 1))
    den = msr + (k - 1) * mse + k * (msc - mse) / n
    return _r((msr - mse) / den) if den > 0 else float("nan")


def bland_altman(total_true, total_pred) -> dict:
    """Acuerdo sobre la PD frente al experto: sesgo (modelo − experto) y límites al 95 %."""
    a, b = np.asarray(total_true, float), np.asarray(total_pred, float)
    dif = b - a
    sesgo = float(np.mean(dif)) if len(dif) else float("nan")
    sd = float(np.std(dif, ddof=1)) if len(dif) > 1 else 0.0
    return {
        "sesgo": _r(sesgo, 2),
        "limite_inferior": _r(sesgo - 1.96 * sd, 2),
        "limite_superior": _r(sesgo + 1.96 * sd, 2),
        "sd_diferencias": _r(sd, 2),
        "n": len(dif),
    }
