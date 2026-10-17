"""Columnas de entrada del modelo A (model/columnas.py): una sola definición para todo."""
import numpy as np
import pandas as pd
import pytest

from grafomotor import ORDEN
from grafomotor.config import Config
from grafomotor.model.columnas import CRUDOS, fila, indicador_de, nombres_columnas
from grafomotor.model.dataset import construir, matriz

FIGURAS = {"F01": {}, "F02": {}, "F03": {}}


def _cfg(entrada: dict | None) -> Config:
    raw = {"figuras": FIGURAS, "modelo": {} if entrada is None else {"entrada": entrada}}
    return Config(raw)


def test_por_defecto_solo_los_6_indicadores():
    assert nombres_columnas(_cfg(None)) == ORDEN


def test_con_crudos_y_figura():
    nombres = nombres_columnas(_cfg({"crudos": True, "figura": "onehot"}))
    assert nombres == ORDEN + list(CRUDOS) + ["fig_F01", "fig_F02", "fig_F03"]


def test_modo_de_figura_desconocido():
    with pytest.raises(ValueError):
        nombres_columnas(_cfg({"figura": "entero"}))


def test_fila_y_matriz_dan_lo_mismo():
    """La inferencia (fila) y el entrenamiento (matriz) deben construir el mismo vector."""
    nombres = nombres_columnas(_cfg({"crudos": True, "figura": "onehot"}))
    valores = {k: 0.1 * (i + 1) for i, k in enumerate(ORDEN)}
    crudos_cortos = {k.removeprefix("raw_"): float(i) for i, k in enumerate(CRUDOS)}
    df = pd.DataFrame([{"child_id": "N1", "figura_id": "F02", **valores,
                        **{"raw_" + k: v for k, v in crudos_cortos.items()}}])
    np.testing.assert_allclose(matriz(df, nombres)[0], fila(valores, crudos_cortos, "F02", nombres))
    assert fila(valores, crudos_cortos, "F02", nombres)[-3:] == [0.0, 1.0, 0.0]


def test_construir_guarda_los_nombres():
    nombres = nombres_columnas(_cfg({"figura": "onehot"}))
    feats = pd.DataFrame([{"child_id": "N1", "figura_id": f, **dict.fromkeys(ORDEN, 0.5)}
                          for f in FIGURAS])
    etq = pd.DataFrame({"child_id": "N1", "figura_id": list(FIGURAS), "edad_meses": 60,
                        "puntaje": [1, 0, 1]})
    datos = construir(feats, etq, nombres)
    assert datos.feature_names == nombres and datos.X.shape == (3, 9)
    assert datos.X[:, 6:].sum(axis=1).tolist() == [1.0, 1.0, 1.0]


def test_indicador_de():
    assert indicador_de("cierre") == "cierre"
    assert indicador_de("raw_extremos_libres") == "cierre"
    assert indicador_de("fig_F05") is None


def test_shap_agrupa_por_indicador():
    """El texto para la docente solo ve indicadores: raw_* se suman a su indicador y fig_* no entran."""
    pytest.importorskip("shap")
    from xgboost import XGBClassifier

    from grafomotor.explain import shap_por_sesion

    nombres = nombres_columnas(_cfg({"crudos": True, "figura": "onehot"}))
    rng = np.random.default_rng(0)
    X = rng.random((60, len(nombres)))
    y = (X[:, 3] + X[:, 9] > 1).astype(int)
    m = XGBClassifier(n_estimators=20, max_depth=2).fit(X, y)
    out = shap_por_sesion(m, X[:5], nombres)
    assert list(out["agg_signed"]) == ORDEN
    c, g = out["columnas"][0], out["por_figura"][0]
    assert g["cierre"] == pytest.approx(c["cierre"] + c["raw_extremos_libres"])


def test_infinito_pasa_a_faltante_igual_en_fila_y_matriz():
    nombres = nombres_columnas(_cfg({"crudos": True}))
    valores = dict.fromkeys(ORDEN, 0.5)
    crudos = {k: 1.0 for k in CRUDOS} | {"raw_dist_interseccion_px": float("inf")}
    df = pd.DataFrame([{"child_id": "N1", "figura_id": "F01", **valores, **crudos}])
    np.testing.assert_array_equal(np.isnan(matriz(df, nombres)[0]),
                                  np.isnan(fila(valores, crudos, "F01", nombres)))
    assert np.isnan(matriz(df, nombres)[0][nombres.index("raw_dist_interseccion_px")])
