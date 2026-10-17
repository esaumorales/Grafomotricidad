"""
Entrenamiento del modelo XGBoost que puntúa cada figura (0/1).

- Validación cruzada AGRUPADA POR NIÑO (GroupKFold): ningún niño en train y test a la vez.
- Grid Search sobre la malla de config.yaml.
- Evaluación con validación ANIDADA: los hiperparámetros se eligen sin ver el fold de prueba.
- Pesos de clase para el desbalance por figura (efecto suelo a los 3 años).
- Punto de corte calibrado (`modelo.umbral`): con pesos balanceados el modelo queda demasiado
  estricto y la PD sale sistemáticamente baja (sesgo). El corte se elige SOLO con los niños de
  entrenamiento y se guarda dentro del modelo (`ModeloConUmbral`), así todo el código que
  compara la probabilidad con 0.5 sigue igual.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.special import expit, logit
from sklearn.metrics import f1_score
from sklearn.model_selection import GridSearchCV, GroupKFold
from xgboost import XGBClassifier

from grafomotor.model.dataset import Datos


class ModeloConUmbral:
    """XGBoost con el punto de corte movido: prob' = sigmoide(logit(prob) + desplazamiento).

    prob' >= 0.5 equivale a prob >= umbral, con umbral = sigmoide(-desplazamiento). Mover el
    log-odds en una constante no cambia el orden de las figuras (misma AUC), solo dónde se
    corta. Para SHAP se usa `base` (el desplazamiento solo cambia el valor base).
    """

    def __init__(self, base: XGBClassifier, desplazamiento: float = 0.0, modo: str = "fijo"):
        self.base, self.desplazamiento, self.modo = base, float(desplazamiento), modo

    @property
    def umbral(self) -> float:
        return float(expit(-self.desplazamiento))

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        p = self.base.predict_proba(X)
        if self.desplazamiento == 0.0:
            return p
        p1 = expit(logit(np.clip(p[:, 1], 1e-6, 1 - 1e-6)) + self.desplazamiento)
        return np.column_stack([1 - p1, p1])

    def predict(self, X: np.ndarray) -> np.ndarray:
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)

    def get_params(self, deep: bool = True) -> dict:
        return self.base.get_params(deep)


@dataclass
class ResultadoEntrenamiento:
    modelo: ModeloConUmbral
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


def _ajustar(X: np.ndarray, y: np.ndarray, params: dict, balanceado: bool) -> XGBClassifier:
    m = XGBClassifier(**params)
    m.fit(X, y, sample_weight=pesos_balanceados(y) if balanceado else None)
    return m


def _modo_umbral(cfg: dict) -> str:
    return (cfg.get("umbral") or {}).get("modo", "fijo")


def desplazamiento_umbral(X: np.ndarray, y: np.ndarray, grupos: np.ndarray, params: dict,
                          cfg: dict) -> float:
    """Desplazamiento del log-odds según `modelo.umbral.modo` (solo con estos datos de entrenamiento).

    - fijo: corte en 0.5 (comportamiento anterior).
    - prevalencia: CV interna agrupada por niño; el corte hace que el modelo marque "correcta"
      tantas figuras como el evaluador (la PD deja de salir baja en promedio).
    - correccion_pesos: deshace en forma analítica el efecto de los pesos balanceados
      (log-odds + log(p/(1-p)), con p = proporción de figuras correctas).
    """
    modo = _modo_umbral(cfg)
    p = float(np.mean(y))
    if modo == "fijo" or p in (0.0, 1.0):
        return 0.0
    balanceado = cfg.get("class_weight") == "balanced"
    if modo == "correccion_pesos":
        return float(np.log(p / (1 - p))) if balanceado else 0.0
    if modo != "prevalencia":
        raise ValueError(f"modelo.umbral.modo desconocido: {modo!r}")
    folds = min(int(cfg.get("cv", {}).get("folds", 5)), len(set(grupos)))
    oof = np.empty(len(y))
    for tr, te in GroupKFold(n_splits=folds).split(X, y, groups=grupos):
        oof[te] = _ajustar(X[tr], y[tr], params, balanceado).predict_proba(X[te])[:, 1]
    corte = float(np.clip(np.quantile(oof, 1 - p), 0.01, 0.99))
    return float(-logit(corte))


def ajustar_con_umbral(X: np.ndarray, y: np.ndarray, grupos: np.ndarray, params: dict,
                       cfg: dict) -> ModeloConUmbral:
    """Ajusta XGBoost con `params` y le pone el punto de corte elegido con estos mismos niños."""
    base = _ajustar(X, y, params, cfg.get("class_weight") == "balanced")
    return ModeloConUmbral(base, desplazamiento_umbral(X, y, grupos, params, cfg),
                           _modo_umbral(cfg))


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
    params = {**_base(cfg).get_params(), **busqueda.best_params_}
    f1s = []
    folds = int(cfg.get("cv", {}).get("folds", 5))
    for tr, te in GroupKFold(n_splits=folds).split(datos.X, datos.y, groups=datos.grupos):
        m = ajustar_con_umbral(datos.X[tr], datos.y[tr], datos.grupos[tr], params, cfg)
        f1s.append(f1_score(datos.y[te], m.predict(datos.X[te]), average="macro"))

    modelo = ModeloConUmbral(
        busqueda.best_estimator_,
        desplazamiento_umbral(datos.X, datos.y, datos.grupos, params, cfg), _modo_umbral(cfg))
    return ResultadoEntrenamiento(
        modelo=modelo,
        mejores_params=busqueda.best_params_,
        cv_f1_macro=float(np.mean(f1s)),
        cv_f1_por_fold=[round(x, 3) for x in f1s],
        feature_names=datos.feature_names,
    )


def ajustar_anidado(datos: Datos, fold: np.ndarray, cfg: dict
                    ) -> tuple[dict[int, ModeloConUmbral], dict[int, dict]]:
    """Validación cruzada ANIDADA (Varma y Simon, 2006).

    Para cada fold externo k, el Grid Search usa SOLO los niños de los otros folds (CV
    interna agrupada por niño) y el mejor modelo predice el fold k, que nunca participó en
    la elección de hiperparámetros. El punto de corte también se elige dentro (solo con los
    niños de entrenamiento del fold). Devuelve un modelo y sus hiperparámetros por fold.
    """
    modelos, params = {}, {}
    for k in sorted(set(fold)):
        tr = fold != k
        busqueda = buscar_hiperparametros(datos.X[tr], datos.y[tr], datos.grupos[tr], cfg)
        completos = {**_base(cfg).get_params(), **busqueda.best_params_}
        m = ModeloConUmbral(
            busqueda.best_estimator_,
            desplazamiento_umbral(datos.X[tr], datos.y[tr], datos.grupos[tr], completos, cfg),
            _modo_umbral(cfg))
        modelos[int(k)] = m
        params[int(k)] = {**busqueda.best_params_, "umbral": round(m.umbral, 3)}
    return modelos, params


def ajustar_por_fold(datos: Datos, fold: np.ndarray, params: dict,
                     cfg: dict) -> dict[int, ModeloConUmbral]:
    """Un XGBoost por fold (entrenado sin los niños de ese fold) con los mismos parámetros.

    Lo usan la evaluación out-of-fold y la prueba de robustez: cada niño se predice con
    un modelo que no lo vio.
    """
    modelos = {}
    for k in sorted(set(fold)):
        tr = fold != k
        modelos[int(k)] = ajustar_con_umbral(datos.X[tr], datos.y[tr], datos.grupos[tr],
                                             params, cfg)
    return modelos
