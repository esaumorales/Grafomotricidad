"""
Entrenamiento del modelo XGBoost que puntúa cada figura (0/1).

- Validación cruzada AGRUPADA POR NIÑO (GroupKFold): ningún niño en train y test a la vez.
- Grid Search sobre la malla de config.yaml.
- Evaluación con validación ANIDADA: los hiperparámetros se eligen sin ver el fold de prueba.
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


def pesos_balanceados(y: np.ndarray) -> np.ndarray:
    """Peso por muestra para que las clases 0 y 1 pesen lo mismo (efecto suelo / techo)."""
    p1 = y.mean()
    w1, w0 = (0.5 / p1 if p1 else 1.0), (0.5 / (1 - p1) if p1 < 1 else 1.0)
    return np.where(y == 1, w1, w0)


SEMILLA_XGB = 20260101


def _base(cfg: dict) -> XGBClassifier:
    return XGBClassifier(objective=cfg.get("objetivo", "binary:logistic"), eval_metric="logloss",
                         tree_method="hist", n_jobs=-1, random_state=SEMILLA_XGB)


def _malla(cfg: dict) -> dict[str, list]:
    grid = cfg.get("grid_search", {})
    return {
        "max_depth": grid.get("max_depth", [3]),
        "learning_rate": grid.get("learning_rate", [0.05]),
        "n_estimators": grid.get("n_estimators", [400]),
        "subsample": grid.get("subsample", [1.0]),
        "reg_lambda": grid.get("reg_lambda", [1.0]),
    }


def buscar_hiperparametros(X: np.ndarray, y: np.ndarray, grupos: np.ndarray,
                           cfg: dict) -> GridSearchCV:
    """Grid Search con CV agrupada por niño sobre (X, y); devuelve la búsqueda reajustada."""
    busqueda = GridSearchCV(
        _base(cfg), _malla(cfg),
        scoring=cfg.get("metrica_busqueda", "f1_macro"),
        cv=GroupKFold(n_splits=int(cfg.get("cv", {}).get("folds", 5))),
        refit=True, n_jobs=-1,
    )
    kw = {"groups": grupos}
    if cfg.get("class_weight") == "balanced":
        kw["sample_weight"] = pesos_balanceados(y)
    busqueda.fit(X, y, **kw)
    return busqueda


def entrenar(datos: Datos, cfg: dict) -> ResultadoEntrenamiento:
    """Modelo FINAL (app web): Grid Search con todos los niños.

    Su cv_f1 es orientativo (elegido y medido con los mismos folds). La estimación honesta
    del rendimiento es la validación anidada (`ajustar_anidado`, comando evaluar-ml).
    """
    busqueda = buscar_hiperparametros(datos.X, datos.y, datos.grupos, cfg)
    balanceado = cfg.get("class_weight") == "balanced"
    f1s = []
    folds = int(cfg.get("cv", {}).get("folds", 5))
    for tr, te in GroupKFold(n_splits=folds).split(datos.X, datos.y, groups=datos.grupos):
        m = XGBClassifier(**{**_base(cfg).get_params(), **busqueda.best_params_})
        m.fit(datos.X[tr], datos.y[tr],
              sample_weight=pesos_balanceados(datos.y[tr]) if balanceado else None)
        f1s.append(f1_score(datos.y[te], m.predict(datos.X[te]), average="macro"))

    return ResultadoEntrenamiento(
        modelo=busqueda.best_estimator_,
        mejores_params=busqueda.best_params_,
        cv_f1_macro=float(np.mean(f1s)),
        cv_f1_por_fold=[round(x, 3) for x in f1s],
        feature_names=datos.feature_names,
    )


def ajustar_anidado(datos: Datos, fold: np.ndarray, cfg: dict
                    ) -> tuple[dict[int, XGBClassifier], dict[int, dict]]:
    """Validación cruzada ANIDADA (Varma y Simon, 2006).

    Para cada fold externo k, el Grid Search usa SOLO los niños de los otros folds (CV
    interna agrupada por niño) y el mejor modelo predice el fold k, que nunca participó en
    la elección de hiperparámetros. Devuelve un modelo y sus hiperparámetros por fold.
    """
    modelos, params = {}, {}
    for k in sorted(set(fold)):
        tr = fold != k
        busqueda = buscar_hiperparametros(datos.X[tr], datos.y[tr], datos.grupos[tr], cfg)
        modelos[int(k)], params[int(k)] = busqueda.best_estimator_, busqueda.best_params_
    return modelos, params


def ajustar_por_fold(datos: Datos, fold: np.ndarray, params: dict,
                     balanceado: bool) -> dict[int, XGBClassifier]:
    """Un XGBoost por fold (entrenado sin los niños de ese fold) con los mismos parámetros.

    Lo usan la evaluación out-of-fold y la prueba de robustez: cada niño se predice con
    un modelo que no lo vio.
    """
    modelos = {}
    for k in sorted(set(fold)):
        tr = fold != k
        m = XGBClassifier(**params)
        m.fit(datos.X[tr], datos.y[tr],
              sample_weight=pesos_balanceados(datos.y[tr]) if balanceado else None)
        modelos[int(k)] = m
    return modelos
