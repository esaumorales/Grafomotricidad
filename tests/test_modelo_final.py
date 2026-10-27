"""Modelo final (Random Forest): decisión por confianza, columnas por criterio y SHAP sobre el pipeline."""
import json

import joblib
import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline

from grafomotor import ORDEN
from grafomotor.explain.shap_values import shap_por_sesion
from grafomotor.model.columnas import indicador_de
from grafomotor.model.final import ModeloFinal

NOMBRES = [*ORDEN[:5], "cr_partes", "dif_extremos", "dif_angulo", "fig_F01", "fig_F02"]


def _pipeline(n=80, seed=0):
    rng = np.random.default_rng(seed)
    X = rng.random((n, len(NOMBRES)))
    X[::7, 5] = np.nan                       # hace que el imputador agregue una columna "falta el dato"
    y = (X[:, 0] + rng.normal(0, .2, n) > .5).astype(int)
    return make_pipeline(SimpleImputer(strategy="median", add_indicator=True),
                         RandomForestClassifier(n_estimators=20, random_state=0)).fit(X, y), X


def test_indicador_de_criterios():
    assert indicador_de("cr_extremos") == "cierre"
    assert indicador_de("dif_cruces") == "intersecciones"
    assert indicador_de("dif_angulo") == "error_angular"
    assert indicador_de("missingindicator_cr_partes") == "precision_modelo"
    assert indicador_de("fig_F03") is None


def test_shap_de_pipeline_con_imputador():
    modelo, X = _pipeline()
    out = shap_por_sesion(modelo, X[:4], NOMBRES)
    assert len(out["por_figura"]) == 4
    assert set(out["agg_signed"]) <= set(ORDEN)
    assert "proporcion" not in out["agg_signed"]
    assert any(k.startswith("missingindicator_") for k in out["columnas"][0])


@pytest.mark.parametrize("p,decision,nota", [(0.10, "incorrecta", 0), (0.25, "incorrecta", 0),
                                              (0.40, "revisar", 0), (0.60, "revisar", 1),
                                              (0.72, "correcta", 1), (0.95, "correcta", 1)])
def test_revision_por_confianza(tmp_path, p, decision, nota):
    modelo, _ = _pipeline()
    joblib.dump(modelo, tmp_path / "modelo.joblib")
    (tmp_path / "manifiesto.json").write_text(json.dumps({
        "version": "prueba", "feature_names": NOMBRES, "punto_de_corte": 0.5,
        "limites_confianza": {"incorrecta_si_prob_menor_o_igual": 0.25, "correcta_si_prob_mayor_o_igual": 0.72},
        "criterios_plantilla": {}, "figuras": ["F01", "F02"]}), encoding="utf-8")
    r = ModeloFinal(tmp_path)._decidir(p)
    assert (r["decision"], r["nota"]) == (decision, nota)
