"""
Entrenamiento del modelo XGBoost que puntúa cada figura (0/1).

- Validación cruzada AGRUPADA POR NIÑO (GroupKFold): ningún niño en train y test a la vez.
- Grid Search sobre la malla de config.yaml.
- Pesos de clase para el desbalance por figura (efecto suelo a los 3 años).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from sklearn.metrics import f1_score
from sklearn.model_selection import GridSearchCV, GroupKFold
from xgboost import XGBClassifier

from grafomotor.model.dataset import Datos


@dataclass
class ResultadoEntrenamiento:
    modelo: XGBClassifier
    mejores_params: dict
    cv_f1_macro: float
    cv_f1_por_fold: list[float] = field(default_factory=list)
    feature_names: list[str] = field(default_factory=list)


def _pesos(y: np.ndarray) -> np.ndarray:
    p1 = y.mean()
    w1, w0 = (0.5 / p1 if p1 else 1.0), (0.5 / (1 - p1) if p1 < 1 else 1.0)
    return np.where(y == 1, w1, w0)


def entrenar(datos: Datos, cfg: dict) -> ResultadoEntrenamiento:
    folds = int(cfg.get("cv", {}).get("folds", 5))
    grid = cfg.get("grid_search", {})

    base = XGBClassifier(
        objective=cfg.get("objetivo", "binary:logistic"),
        eval_metric="logloss",
        tree_method="hist",
        n_jobs=-1,
        random_state=20260101,
    )
    param_grid = {
        "max_depth": grid.get("max_depth", [3]),
        "learning_rate": grid.get("learning_rate", [0.05]),
        "n_estimators": grid.get("n_estimators", [400]),
        "subsample": grid.get("subsample", [1.0]),
        "reg_lambda": grid.get("reg_lambda", [1.0]),
    }

    search = GridSearchCV(
        base, param_grid,
        scoring="f1_macro",
        cv=GroupKFold(n_splits=folds),
        refit=True,
        n_jobs=-1,
    )
    fit_kw = {"groups": datos.grupos}
    if cfg.get("class_weight") == "balanced":
        fit_kw["sample_weight"] = _pesos(datos.y)
    search.fit(datos.X, datos.y, **fit_kw)

    # F1 por fold con los mejores params (para reportar variabilidad)
    f1s = []
    for tr, te in GroupKFold(n_splits=folds).split(datos.X, datos.y, groups=datos.grupos):
        m = XGBClassifier(**{**base.get_params(), **search.best_params_})
        sw = _pesos(datos.y[tr]) if cfg.get("class_weight") == "balanced" else None
        m.fit(datos.X[tr], datos.y[tr], sample_weight=sw)
        f1s.append(f1_score(datos.y[te], m.predict(datos.X[te]), average="macro"))

    return ResultadoEntrenamiento(
        modelo=search.best_estimator_,
        mejores_params=search.best_params_,
        cv_f1_macro=float(np.mean(f1s)),
        cv_f1_por_fold=[round(x, 3) for x in f1s],
        feature_names=datos.feature_names,
    )
