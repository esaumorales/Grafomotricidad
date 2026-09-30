"""
Comparación estadística entre dos modelos evaluados sobre los MISMOS niños y figuras.

  - McNemar exacto por figura (y global): ¿aciertan en proporciones distintas
    frente al experto sobre los mismos casos?
  - Bootstrap por niño (se remuestrean niños, no figuras, para respetar la
    dependencia entre las 15 figuras de un mismo niño): IC 95 % de la diferencia
    de kappa por figura y de CCI de la PD (modelo B − modelo A).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import binomtest
from sklearn.metrics import cohen_kappa_score

from grafomotor.evaluation.metrics import icc_acuerdo_absoluto


def mcnemar_exacto(y, pred_a, pred_b) -> dict:
    """McNemar exacto (binomial sobre los pares discordantes)."""
    y, a, b = (np.asarray(v, int) for v in (y, pred_a, pred_b))
    ok_a, ok_b = a == y, b == y
    solo_a = int(np.sum(ok_a & ~ok_b))   # A acierta, B falla
    solo_b = int(np.sum(~ok_a & ok_b))   # B acierta, A falla
    n = solo_a + solo_b
    p = 1.0 if n == 0 else float(binomtest(solo_a, n, 0.5).pvalue)
    return {"solo_A_acierta": solo_a, "solo_B_acierta": solo_b, "p_valor": round(p, 4)}


def unir(oof_a: pd.DataFrame, oof_b: pd.DataFrame) -> pd.DataFrame:
    """Casos medidos por ambos modelos (intersección), con el mismo criterio experto."""
    cols = ["child_id", "figura_id", "edad_meses", "y", "yhat"]
    m = oof_a[cols].merge(oof_b[["child_id", "figura_id", "y", "yhat"]],
                          on=["child_id", "figura_id"], suffixes=("_A", "_B"),
                          validate="one_to_one")
    if not (m["y_A"] == m["y_B"]).all():
        raise ValueError("los dos modelos no usan las mismas etiquetas del experto")
    return m.rename(columns={"y_A": "y"}).drop(columns="y_B")


def holm(p_valores: dict[str, float]) -> dict[str, float]:
    """Corrección de Holm-Bonferroni (controla el error familiar entre las 15 figuras)."""
    orden = sorted(p_valores, key=p_valores.get)
    m, ajustados, maximo = len(orden), {}, 0.0
    for i, clave in enumerate(orden):
        maximo = max(maximo, min(1.0, (m - i) * p_valores[clave]))
        ajustados[clave] = round(maximo, 4)
    return ajustados


def mcnemar_por_figura(unidos: pd.DataFrame) -> dict:
    """McNemar global y por figura; las figuras llevan además el p corregido por Holm."""
    medidos = unidos.dropna(subset=["yhat_A", "yhat_B"])
    por_figura = {str(fig): mcnemar_exacto(g["y"], g["yhat_A"], g["yhat_B"])
                  for fig, g in medidos.groupby("figura_id")}
    p_holm = holm({f: r["p_valor"] for f, r in por_figura.items()})
    for f, r in por_figura.items():
        r["p_holm"] = p_holm[f]
    return {"global": mcnemar_exacto(medidos["y"], medidos["yhat_A"], medidos["yhat_B"]),
            **por_figura}


def bootstrap_diferencias(unidos: pd.DataFrame, n_boot: int = 2000,
                          semilla: int = 20260930) -> dict:
    """IC 95 % percentil de (B − A) para kappa por figura y CCI de la PD."""
    rng = np.random.default_rng(semilla)
    ninos = np.array(sorted(unidos["child_id"].unique()))
    pos = {c: i for i, c in enumerate(ninos)}

    # kappa: solo casos medidos por ambos; se guardan los índices de fila por niño
    med = unidos.dropna(subset=["yhat_A", "yhat_B"]).reset_index(drop=True)
    y = med["y"].to_numpy(int)
    a = med["yhat_A"].to_numpy(int)
    b = med["yhat_B"].to_numpy(int)
    filas_de = [[] for _ in ninos]
    for i, c in enumerate(med["child_id"]):
        filas_de[pos[c]].append(i)
    filas_de = [np.array(f, int) for f in filas_de]

    # CCI: PD por niño (fallos = 0)
    g = unidos.assign(A=unidos["yhat_A"].fillna(0), B=unidos["yhat_B"].fillna(0))
    pdn = g.groupby("child_id")[["y", "A", "B"]].sum().loc[ninos].to_numpy(float)

    def _dif(idx_ninos):
        filas = np.concatenate([filas_de[i] for i in idx_ninos])
        dk = (cohen_kappa_score(y[filas], b[filas]) - cohen_kappa_score(y[filas], a[filas])
              if len(filas) else np.nan)
        p = pdn[idx_ninos]
        dc = icc_acuerdo_absoluto(p[:, 0], p[:, 2]) - icc_acuerdo_absoluto(p[:, 0], p[:, 1])
        return dk, dc

    obs_k, obs_c = _dif(np.arange(len(ninos)))
    dk, dc = zip(*(_dif(rng.integers(0, len(ninos), len(ninos))) for _ in range(n_boot)),
                  strict=True)

    def _ic(obs, v):
        v = np.asarray(v, float)
        v = v[np.isfinite(v)]
        lo, hi = np.percentile(v, [2.5, 97.5]) if len(v) else (np.nan, np.nan)
        return {"diferencia_B_menos_A": round(float(obs), 3),
                "ic95": [round(float(lo), 3), round(float(hi), 3)],
                "incluye_0": bool(lo <= 0 <= hi)}

    return {"n_boot": n_boot, "kappa_figura": _ic(obs_k, dk), "cci_PD": _ic(obs_c, dc)}


def comparar(oof_a: pd.DataFrame, oof_b: pd.DataFrame, n_boot: int = 2000) -> dict:
    unidos = unir(oof_a, oof_b)
    return {
        "n_casos_comunes": len(unidos.dropna(subset=["yhat_A", "yhat_B"])),
        "mcnemar": mcnemar_por_figura(unidos),
        "bootstrap": bootstrap_diferencias(unidos, n_boot),
    }
