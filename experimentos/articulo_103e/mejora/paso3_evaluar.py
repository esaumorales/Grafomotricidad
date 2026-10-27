"""Mejora del Random Forest, evaluada SOLO con los 83 niños de desarrollo (5 pliegues por niño,
los mismos de paso1_red.py). Los 20 niños de prueba no se usan aquí.

Variantes (cada una agrega algo a la anterior):
  V0 base       RF con indicadores generales + por criterio, sin proporción, corte global
  V1 +criterios2  indicadores nuevos (huecos, rectitud, ángulos rectos, redondez, posición)
  V2 +corte por figura
  V3 +red        probabilidad de EfficientNet-B0 como variable
  V4 -redundantes  quita columnas con correlación > 0.95 (calculada con el entrenamiento)
Regla fijada antes de ver resultados: se elige la variante con mayor kappa por figura; si la
diferencia con una más simple es menor que 0.01, se queda la más simple."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.special import expit, logit
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import cohen_kappa_score
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.pipeline import make_pipeline

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from criterios import _dif_angular  # noqa: E402
from grafomotor.config import load_config
from grafomotor.evaluation.metrics import icc_acuerdo_absoluto
from grafomotor.io import cargar_etiquetas
from grafomotor.model.columnas import nombres_columnas
from grafomotor.model.dataset import matriz
from grafomotor.model.train import pesos_balanceados

SEM = 20260930
cfg = load_config("../config.yaml")
CR = ["partes", "partes_juntas", "dist_partes", "extremos", "cruces", "ondas", "esquinas", "giro_max", "incl_partes"]


def construir_datos() -> tuple[pd.DataFrame, dict]:
    feat = pd.read_parquet("../processed/features.parquet")
    cr = pd.read_parquet("../processed/criterios.parquet")
    from criterios import medir
    from grafomotor.io import a_binaria, leer_gris
    ref = {f: medir(a_binaria(leer_gris(cfg.ruta("templates") / f"{f}.png"))) for f in cfg.figuras}
    for c in CR + ["angulo"]:
        refc = cr["figura_id"].map(lambda f: ref[f][c]).astype(float)
        cr[f"cr_{c}"] = cr[c].astype(float)
        cr[f"dif_{c}"] = ([_dif_angular(a, b) for a, b in zip(cr[c], refc)] if c == "angulo"
                          else (cr[c].astype(float) - refc).abs())
    nuevas = [f"cr_{c}" for c in CR] + [f"dif_{c}" for c in CR + ["angulo"]]
    c2 = pd.read_parquet("criterios2.parquet")
    red = pd.read_parquet("prob_red.parquet")
    etq = cargar_etiquetas(cfg.ruta("labels"))
    d = (etq.merge(feat, on=["child_id", "figura_id"])
            .merge(cr[["child_id", "figura_id"] + nuevas], on=["child_id", "figura_id"])
            .merge(c2, on=["child_id", "figura_id"])
            .merge(red, on=["child_id", "figura_id"]).reset_index(drop=True))
    base = [c for c in nombres_columnas(cfg) if c not in ("proporcion", "raw_razon_aspecto")] + nuevas
    c2cols = [c for c in c2.columns if c.startswith(("cr2_", "dif2_"))]
    return d, {"base": base, "c2": c2cols}


EST = make_pipeline(SimpleImputer(strategy="median", add_indicator=True),
                    RandomForestClassifier(n_estimators=300, random_state=SEM, n_jobs=6))
MALLA = {"randomforestclassifier__max_depth": [3, 5, None],
         "randomforestclassifier__min_samples_leaf": [1, 5, 10]}
KW = lambda y: {"randomforestclassifier__sample_weight": pesos_balanceados(y)}  # noqa: E731


def sin_redundantes(X: np.ndarray, cols: list[str], umbral: float = 0.95) -> list[int]:
    c = pd.DataFrame(X, columns=cols).corr().abs().to_numpy()
    quitar = set()
    for i in range(len(cols)):
        if i in quitar:
            continue
        for j in range(i + 1, len(cols)):
            if c[i, j] > umbral:
                quitar.add(j)
    return [i for i in range(len(cols)) if i not in quitar]


def ajustar(X, y, g, fig, corte_por_figura: bool):
    """Grid interno por niño + corte por prevalencia (global o por figura) con probabilidades
    fuera de pliegue internas. Devuelve el modelo y una función de corte."""
    b = GridSearchCV(clone(EST), MALLA, scoring="f1_macro", cv=GroupKFold(5), n_jobs=1)
    b.fit(X, y, groups=g, **KW(y))
    oof = np.empty(len(y))
    for tr, te in GroupKFold(5).split(X, y, groups=g):
        m = clone(b.best_estimator_); m.fit(X[tr], y[tr], **KW(y[tr])); oof[te] = m.predict_proba(X[te])[:, 1]
    glob = float(np.clip(np.quantile(oof, 1 - y.mean()), 0.01, 0.99))
    cortes = {}
    if corte_por_figura:
        for f in np.unique(fig):
            s = fig == f
            cortes[f] = float(np.clip(np.quantile(oof[s], 1 - y[s].mean()), 0.01, 0.99))
    return b.best_estimator_, (lambda p, fg: np.array([cortes.get(f, glob) for f in fg]) if cortes
                               else np.full(len(p), glob)), b.best_params_


def variante(d, cols, corte_fig, quitar_red):
    X = matriz(d, cols); y = d.puntaje.to_numpy().astype(int); g = d.child_id.to_numpy(); fig = d.figura_id.to_numpy()
    prob, yhat = np.empty(len(y)), np.empty(len(y))
    for k in range(5):
        tr, te = (d.pliegue != k).to_numpy(), (d.pliegue == k).to_numpy()
        idx = sin_redundantes(X[tr], cols) if quitar_red else list(range(len(cols)))
        m, corte, _ = ajustar(X[tr][:, idx], y[tr], g[tr], fig[tr], corte_fig)
        prob[te] = m.predict_proba(X[te][:, idx])[:, 1]
        yhat[te] = (prob[te] >= corte(prob[te], fig[te])).astype(int)
    return d[["child_id", "figura_id"]].assign(y=y, prob=prob, yhat=yhat)


def medidas(o):
    pdn = o.groupby("child_id").agg(r=("y", "sum"), p=("yhat", "sum"))
    return {"kappa": round(cohen_kappa_score(o.y, o.yhat), 3),
            "cci": round(icc_acuerdo_absoluto(pdn.r, pdn.p), 3),
            "error_PD": round(float((pdn.p - pdn.r).abs().mean()), 2),
            "sesgo_PD_baja": round(float((pdn.p - pdn.r)[pdn.r <= 4].mean()), 2),
            "kappa_fig": {f: round(cohen_kappa_score(s.y, s.yhat), 2) for f, s in o.groupby("figura_id")}}


if __name__ == "__main__":
    d, C = construir_datos()
    dev = d[d.conjunto == "desarrollo"].reset_index(drop=True)
    V = {"V0_base": (C["base"], False, False),
         "V1_criterios2": (C["base"] + C["c2"], False, False),
         "V2_corte_figura": (C["base"] + C["c2"], True, False),
         "V3_red": (C["base"] + C["c2"] + ["prob_red"], True, False),
         "V4_sin_redundantes": (C["base"] + C["c2"] + ["prob_red"], True, True)}
    res = {}
    for n, (cols, cf, qr) in V.items():
        o = variante(dev, cols, cf, qr); o.to_parquet(f"oof_dev_{n}.parquet")
        res[n] = {"n_columnas": len(cols), **medidas(o)}
        print(n, json.dumps({k: v for k, v in res[n].items() if k != "kappa_fig"}), flush=True)
    json.dump(res, open("evaluacion_desarrollo.json", "w"), indent=2)
