"""Métricas comunes, PD con regla de parada, particiones por niño y comparación A vs B."""
import numpy as np
import pandas as pd
import pytest

from grafomotor.evaluation.comparacion import comparar, mcnemar_exacto
from grafomotor.evaluation.degradaciones import DEGRADACIONES, degradar
from grafomotor.evaluation.metrics import icc_acuerdo_absoluto, metricas_binarias
from grafomotor.evaluation.particiones import crear_particiones
from grafomotor.scoring.pd import pd_completa, pd_manual


def test_kappa_no_se_deja_engañar_por_la_clase_mayoritaria():
    # 90 % correctas: un modelo que siempre dice "correcta" tiene 90 % de exactitud y kappa 0
    y = np.array([1] * 90 + [0] * 10)
    m = metricas_binarias(y, np.ones(100, int))
    assert m["exactitud"] == 0.9
    assert m["kappa"] == 0.0
    assert m["especificidad"] == 0.0


def test_metricas_binarias_perfectas():
    y = np.array([0, 1, 1, 0, 1])
    m = metricas_binarias(y, y)
    assert m["kappa"] == 1.0 and m["sensibilidad"] == 1.0 and m["especificidad"] == 1.0


def test_icc_acuerdo_absoluto():
    a = np.array([3, 5, 8, 10, 12, 15])
    assert icc_acuerdo_absoluto(a, a) == 1.0
    # un sesgo constante baja el CCI de acuerdo absoluto aunque la correlación sea 1
    assert icc_acuerdo_absoluto(a, a + 3) < 0.9
    # ejemplo clásico de Shrout y Fleiss (1979, tabla 2): ICC(2,1) = 0.29
    sf = np.array([[9, 2, 5, 8], [6, 1, 3, 2], [8, 4, 6, 8],
                   [7, 1, 2, 6], [10, 5, 6, 9], [6, 2, 4, 7]])
    assert icc_acuerdo_absoluto(*sf.T) == pytest.approx(0.29, abs=0.005)


def test_pd_manual_regla_4_fallos():
    p = [1, 1, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0, 1]
    assert pd_completa(p) == 6
    assert pd_manual(p) == 2            # tras F03-F06 (4 ceros seguidos) ya no cuenta nada
    assert pd_manual([1, 0, 0, 0, 1] + [1] * 10) == 12   # 3 ceros seguidos no paran
    d = {f"F{i:02d}": v for i, v in enumerate(p, 1)}
    assert pd_manual(d) == 2            # dict -> se ordena F01..F15


def test_particiones_agrupadas_por_nino():
    rng = np.random.default_rng(0)
    et = pd.DataFrame([{"child_id": f"N{i:03d}", "figura_id": f"F{j:02d}",
                        "puntaje": int(rng.random() < 0.6)}
                       for i in range(40) for j in range(1, 16)])
    part = crear_particiones(et, 5)
    assert set(part["child_id"]) == set(et["child_id"])
    assert not part["child_id"].duplicated().any()
    assert part["fold"].nunique() == 5
    # reproducible
    assert part.equals(crear_particiones(et, 5))


def test_mcnemar():
    y = np.ones(20, int)
    a = np.ones(20, int)
    b = np.array([1] * 10 + [0] * 10)
    r = mcnemar_exacto(y, a, b)
    assert r["solo_A_acierta"] == 10 and r["solo_B_acierta"] == 0
    assert r["p_valor"] < 0.01
    assert mcnemar_exacto(y, a, a)["p_valor"] == 1.0


def _oof(yhat_ruido, semilla):
    rng = np.random.default_rng(semilla)
    filas = []
    for i in range(30):
        for j in range(1, 16):
            y = int(rng.random() < 0.6)
            yhat = y if rng.random() > yhat_ruido else 1 - y
            filas.append({"child_id": f"N{i:03d}", "figura_id": f"F{j:02d}", "edad_meses": 50,
                          "fold": i % 5, "y": y, "yhat": float(yhat), "prob": float(yhat)})
    return pd.DataFrame(filas)


def test_comparar_mismo_modelo_diferencia_cero():
    a = _oof(0.1, 1)
    r = comparar(a, a.copy(), n_boot=50)
    assert r["bootstrap"]["kappa_figura"]["diferencia_B_menos_A"] == 0.0
    assert r["mcnemar"]["global"]["p_valor"] == 1.0


def test_comparar_exige_mismas_etiquetas():
    a, b = _oof(0.1, 1), _oof(0.1, 2)
    with pytest.raises(ValueError):
        comparar(a, b, n_boot=10)


@pytest.mark.parametrize("tipo", list(DEGRADACIONES))
def test_degradaciones_mantienen_forma(tipo):
    img = np.full((300, 200), 230, np.uint8)
    img[100:200, 50:150] = 30
    out = degradar(img, tipo, "fuerte", 0)
    assert out.shape == img.shape and out.dtype == np.uint8
    assert not np.array_equal(out, img)
