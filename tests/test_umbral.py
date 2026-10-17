"""Punto de corte calibrado del modelo A (model/train.py): corrige que la PD salga baja."""
import numpy as np
import pytest
from scipy.special import expit

from grafomotor.model.train import (
    ModeloConUmbral,
    ajustar_con_umbral,
    desplazamiento_umbral,
)

PARAMS = {"n_estimators": 40, "max_depth": 2, "learning_rate": 0.1, "random_state": 0}


def _datos(n_ninos=40, por_nino=15, semilla=0):
    """66 % de unos, como en los datos reales: los pesos balanceados empujan hacia 0."""
    rng = np.random.default_rng(semilla)
    n = n_ninos * por_nino
    X = rng.random((n, 4))
    y = (X[:, 0] + 0.6 * rng.random(n) > 0.6).astype(int)
    grupos = np.repeat(np.arange(n_ninos), por_nino)
    return X, y, grupos


def test_fijo_no_mueve_nada():
    X, y, g = _datos()
    assert desplazamiento_umbral(X, y, g, PARAMS, {"umbral": {"modo": "fijo"}}) == 0.0
    assert desplazamiento_umbral(X, y, g, PARAMS, {}) == 0.0


def test_correccion_pesos_es_el_log_odds_de_la_prevalencia():
    X, y, g = _datos()
    cfg = {"class_weight": "balanced", "umbral": {"modo": "correccion_pesos"}}
    p = y.mean()
    assert desplazamiento_umbral(X, y, g, PARAMS, cfg) == pytest.approx(np.log(p / (1 - p)))
    sin_pesos = {"umbral": {"modo": "correccion_pesos"}}
    assert desplazamiento_umbral(X, y, g, PARAMS, sin_pesos) == 0.0


def test_prevalencia_quita_el_sesgo_hacia_abajo():
    """Con pesos balanceados y corte 0.5 el modelo marca menos 'correctas' que el evaluador."""
    X, y, g = _datos()
    tr, te = g < 30, g >= 30
    base = {"class_weight": "balanced", "cv": {"folds": 5}}
    fijo = ajustar_con_umbral(X[tr], y[tr], g[tr], PARAMS, {**base, "umbral": {"modo": "fijo"}})
    prev = ajustar_con_umbral(X[tr], y[tr], g[tr], PARAMS,
                              {**base, "umbral": {"modo": "prevalencia"}})
    real = y[te].mean()
    assert fijo.predict(X[te]).mean() < real                    # el sesgo existe
    assert abs(prev.predict(X[te]).mean() - real) < abs(fijo.predict(X[te]).mean() - real)


def test_desplazar_no_cambia_el_orden():
    X, y, g = _datos()
    m = ajustar_con_umbral(X, y, g, PARAMS, {"umbral": {"modo": "fijo"}})
    movido = ModeloConUmbral(m.base, 0.8, "prueba")
    p0, p1 = m.predict_proba(X)[:, 1], movido.predict_proba(X)[:, 1]
    assert np.array_equal(np.argsort(p0, kind="stable"), np.argsort(p1, kind="stable"))
    assert movido.umbral == pytest.approx(expit(-0.8))
    assert np.array_equal(movido.predict(X), (p0 >= movido.umbral).astype(int))


def test_modo_desconocido():
    X, y, g = _datos()
    with pytest.raises(ValueError):
        desplazamiento_umbral(X, y, g, PARAMS, {"umbral": {"modo": "otro"}})


def test_shap_funciona_con_el_modelo_envuelto():
    pytest.importorskip("shap")
    from grafomotor import ORDEN
    from grafomotor.explain import shap_por_sesion

    rng = np.random.default_rng(1)
    X = rng.random((80, 6))
    y = (X[:, 0] > 0.4).astype(int)
    g = np.repeat(np.arange(16), 5)
    m = ajustar_con_umbral(X, y, g, PARAMS, {"umbral": {"modo": "prevalencia"}})
    out = shap_por_sesion(m, X[:3], ORDEN)
    assert list(out["agg_signed"]) == ORDEN
