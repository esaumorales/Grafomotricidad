"""Identificación de niños en riesgo, calibración, datos suficientes y validación por colegio."""
import numpy as np
import pandas as pd
import pytest

from grafomotor.comandos.curva_aprendizaje import submuestra_ninos
from grafomotor.comandos.validar import balance_por_figura
from grafomotor.evaluation.calibracion import error_calibracion, platt_cruzado
from grafomotor.evaluation.identificacion import (
    curva_selectiva,
    distribucion_pd,
    metricas_tamizaje,
    triaje,
    wilson,
)
from grafomotor.evaluation.particiones import crear_particiones, obtener_particiones


# --- identificación ------------------------------------------------------------
def test_distribucion_pd_es_poisson_binomial():
    d = distribucion_pd([0.5, 0.5])
    assert np.allclose(d, [0.25, 0.5, 0.25])
    d = distribucion_pd([0.9] * 15)
    assert d.shape == (16,) and d.sum() == pytest.approx(1.0)
    assert np.argmax(d) == 14                      # lo más probable: 13-14 aciertos


def test_wilson_conocido():
    lo, hi = wilson(8, 10)
    assert lo == pytest.approx(0.490, abs=0.002)   # IC de Wilson de 8/10: [0.490, 0.943]
    assert hi == pytest.approx(0.943, abs=0.002)
    assert np.isnan(wilson(0, 0)[0])


def test_metricas_de_tamizaje():
    m = metricas_tamizaje([1, 1, 0, 0], [1, 0, 0, 1])
    assert m["sensibilidad"]["valor"] == 0.5 and m["especificidad"]["valor"] == 0.5
    assert m["confusion"] == {"VP": 1, "FN": 1, "VN": 1, "FP": 1}


def test_triaje_manda_la_zona_gris_a_revision():
    ninos = pd.DataFrame({"p_riesgo": [0.95, 0.05, 0.5, 0.3],
                          "riesgo_real": [1, 0, 1, 1]})
    t = triaje(ninos, 0.2, 0.8)
    assert t["a_revision"]["n"] == 2
    assert t["a_revision"]["de_ellos_en_riesgo_real"] == 2
    assert t["en_riesgo_no_detectados"] == 0
    assert t["decididos_automaticamente"]["sensibilidad"]["valor"] == 1.0


def test_curva_selectiva_mejora_al_quitar_los_dudosos():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, 400)
    seguro = rng.random(400) < 0.5
    prob = np.where(seguro, np.where(y == 1, 0.95, 0.05), rng.random(400))
    c = curva_selectiva(pd.DataFrame({"y": y, "prob": prob}), col_prob="prob",
                        coberturas=(1.0, 0.5))
    assert c[1]["kappa"] > c[0]["kappa"]


# --- calibración ------------------------------------------------------------------
def test_platt_cruzado_mejora_una_prob_descalibrada():
    rng = np.random.default_rng(1)
    n = 2000
    verdad = rng.random(n)
    y = (rng.random(n) < verdad).astype(int)
    prob = np.clip(verdad ** 0.3, 0.01, 0.99)       # sistemáticamente demasiado alta
    oof = pd.DataFrame({"y": y, "prob": prob, "fold": np.arange(n) % 5})
    cal = platt_cruzado(oof)
    assert error_calibracion(y, cal)["ece"] < error_calibracion(y, prob)["ece"]
    assert cal.notna().all()


# --- ¿alcanzan los datos? --------------------------------------------------------
def test_balance_por_figura_detecta_la_clase_minoritaria():
    df = pd.DataFrame({"figura_id": ["F01"] * 10 + ["F02"] * 10,
                       "puntaje": [1] * 9 + [0] + [1] * 5 + [0] * 5})
    b = balance_por_figura(df, min_ml=3, min_dl=6).set_index("figura_id")
    assert b.loc["F01", "minoritaria"] == 1 and not b.loc["F01", "alcanza_A"]
    assert b.loc["F02", "alcanza_A"] and not b.loc["F02", "alcanza_B"]


def test_submuestra_de_ninos_reproducible():
    ninos = np.array([f"N{i}" for i in range(100)])
    a = submuestra_ninos(ninos, 0.2, 7)
    assert len(a) == 20 and a == submuestra_ninos(ninos, 0.2, 7)


# --- validación externa por colegio ----------------------------------------------
def _etiquetas_colegios():
    return pd.DataFrame([{"child_id": f"{c}{i}", "figura_id": f"F{j:02d}", "puntaje": 1,
                          "colegio": c}
                         for c in ("NANA", "BUEN_PASTOR") for i in range(5)
                         for j in range(1, 4)])


def test_particiones_por_colegio_un_fold_por_colegio(tmp_path):
    et = _etiquetas_colegios()
    p = crear_particiones(et, por="colegio")
    assert p["fold"].nunique() == 2
    por_colegio = p.merge(et.drop_duplicates("child_id"), on="child_id")
    assert por_colegio.groupby("colegio")["fold"].nunique().eq(1).all()
    # cambiar de criterio regenera el archivo
    ruta = tmp_path / "particiones.csv"
    obtener_particiones(ruta, et, 5, por="colegio")
    assert pd.read_csv(ruta)["criterio"].iloc[0] == "colegio"


def test_particiones_por_colegio_exigen_la_columna():
    with pytest.raises(ValueError, match="colegio"):
        crear_particiones(_etiquetas_colegios().drop(columns="colegio"), por="colegio")
