"""
Calibración de las probabilidades por figura.

Los pesos por clase (que compensan el desbalance) desplazan las probabilidades: un 0.7 del
modelo no significa "70 % de las veces es correcta". Para IDENTIFICAR niños en riesgo a
partir de esas probabilidades hace falta que sí lo signifiquen.

Calibración cruzada de Platt, sin reentrenar y sin mirar el fold que se calibra: las
predicciones del fold k se recalibran con una regresión logística sobre el logit, ajustada
con las predicciones out-of-fold (y las etiquetas) de los OTROS folds.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

EPS = 1e-4


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(p, float), EPS, 1 - EPS)
    return np.log(p / (1 - p))


def platt_cruzado(oof: pd.DataFrame) -> pd.Series:
    """Probabilidad calibrada para cada fila (NaN donde no hubo predicción)."""
    calibrada = pd.Series(np.nan, index=oof.index)
    medidas = oof["prob"].notna()
    for k in sorted(oof["fold"].unique()):
        ajuste = medidas & (oof["fold"] != k)
        aplicar = medidas & (oof["fold"] == k)
        if not aplicar.any():
            continue
        if oof.loc[ajuste, "y"].nunique() < 2:
            calibrada[aplicar] = oof.loc[aplicar, "prob"]
            continue
        lr = LogisticRegression(C=1e6)   # sin regularización apreciable: Platt clásico
        lr.fit(_logit(oof.loc[ajuste, "prob"]).reshape(-1, 1), oof.loc[ajuste, "y"])
        calibrada[aplicar] = lr.predict_proba(_logit(oof.loc[aplicar, "prob"]).reshape(-1, 1))[:, 1]
    return calibrada


def error_calibracion(y, p, n_bins: int = 10) -> dict:
    """Brier y error de calibración esperado (ECE) con intervalos de igual ancho."""
    y, p = np.asarray(y, float), np.asarray(p, float)
    ok = np.isfinite(p)
    y, p = y[ok], p[ok]
    if not len(y):
        return {"brier": float("nan"), "ece": float("nan"), "n": 0}
    bins = np.minimum((p * n_bins).astype(int), n_bins - 1)
    ece = sum(abs(y[bins == b].mean() - p[bins == b].mean()) * (bins == b).mean()
              for b in range(n_bins) if (bins == b).any())
    return {"brier": round(float(np.mean((p - y) ** 2)), 4), "ece": round(float(ece), 4),
            "n": len(y)}
