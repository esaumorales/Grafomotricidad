"""Antes y después de agregar los indicadores por criterio del manual (criterios.py).
Mismo protocolo que otros_ml.py / evaluar-ml: mismas particiones por niño (exp67), Grid Search
interno agrupado por niño (f1_macro, pesos balanceados) y corte por prevalencia elegido solo con
los niños de entrenamiento. Tres modelos de ML x tres variantes de columnas."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from grafomotor.config import load_config
from grafomotor.evaluation.particiones import folds_de, particiones_de_config
from grafomotor.evaluation.reporte import evaluar_oof, resumen_corto
from grafomotor.io import a_binaria, cargar_etiquetas, leer_gris
from grafomotor.model.columnas import nombres_columnas
from grafomotor.model.dataset import matriz
from grafomotor.model.train import pesos_balanceados
from grafomotor.scoring.baremo import cargar_baremo
from grafomotor.scoring.niveles import CriterioNiveles

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI))
from criterios import _dif_angular, medir  # noqa: E402

cfg = load_config(AQUI / "config.yaml")
SEM = 20260930
CR = ["partes", "partes_juntas", "dist_partes", "extremos", "cruces", "ondas", "esquinas",
      "giro_max", "incl_partes"]

# 1) indicadores por criterio (se guardan para no recalcular)
cache = AQUI / "processed/criterios.parquet"
feat = pd.read_parquet(AQUI / "processed/features.parquet")
if cache.exists():
    cr = pd.read_parquet(cache)
else:
    interim = Path(cfg.ruta("interim")); filas = []
    for r in feat[["child_id", "figura_id"]].itertuples(index=False):
        p = interim / f"{r.child_id}__{r.figura_id}.png"
        filas.append({"child_id": r.child_id, "figura_id": r.figura_id,
                      **(medir(a_binaria(leer_gris(p))) if p.exists() else {})})
    cr = pd.DataFrame(filas); cr.to_parquet(cache)
ref = {f: medir(a_binaria(leer_gris(cfg.ruta("templates") / f"{f}.png"))) for f in cfg.get("figuras")}
for c in CR + ["angulo"]:
    refc = cr["figura_id"].map(lambda f: ref[f][c]).astype(float)
    cr[f"cr_{c}"] = cr[c].astype(float)
    cr[f"dif_{c}"] = ([_dif_angular(a, b) for a, b in zip(cr[c], refc)] if c == "angulo"
                      else (cr[c].astype(float) - refc).abs())
nuevas = [f"cr_{c}" for c in CR] + [f"dif_{c}" for c in CR + ["angulo"]]
feat = feat.merge(cr[["child_id", "figura_id"] + nuevas], on=["child_id", "figura_id"], how="left")

etq = cargar_etiquetas(cfg.ruta("labels"))
part = particiones_de_config(cfg, etq)
datos = etq.merge(feat, on=["child_id", "figura_id"]).reset_index(drop=True)
datos["fold"] = folds_de(datos["child_id"], part)
y, g = datos["puntaje"].to_numpy().astype(int), datos["child_id"].to_numpy()
baremo, crit = cargar_baremo(cfg.ruta("baremos")), CriterioNiveles.de_config(cfg)

base = nombres_columnas(cfg)
sin_prop = [c for c in base if c not in ("proporcion", "raw_razon_aspecto")]
VARIANTES = {"antes": base, "con_criterios": base + nuevas, "con_criterios_sin_proporcion": sin_prop + nuevas}
MODELOS = {
    "xgboost": (XGBClassifier(objective="binary:logistic", eval_metric="logloss", random_state=SEM,
                              n_jobs=4, verbosity=0),
                {"max_depth": [2, 3, 4], "learning_rate": [0.03, 0.1], "n_estimators": [200, 400],
                 "reg_lambda": [1.0, 3.0]}, None),
    "reg_logistica": (make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(),
                                    LogisticRegression(max_iter=5000)),
                      {"logisticregression__C": [0.01, 0.1, 1, 10]}, "logisticregression"),
    "random_forest": (make_pipeline(SimpleImputer(strategy="median", add_indicator=True),
                                    RandomForestClassifier(n_estimators=300, random_state=SEM, n_jobs=4)),
                      {"randomforestclassifier__max_depth": [3, 5, None],
                       "randomforestclassifier__min_samples_leaf": [1, 5, 10]}, "randomforestclassifier"),
}


def kw(paso, y):
    return {("%s__sample_weight" % paso if paso else "sample_weight"): pesos_balanceados(y)}


def desplazamiento(est, paso, X, y, g):
    oof = np.empty(len(y))
    for tr, te in GroupKFold(5).split(X, y, groups=g):
        m = clone(est); m.fit(X[tr], y[tr], **kw(paso, y[tr])); oof[te] = m.predict_proba(X[te])[:, 1]
    return -logit(float(np.clip(np.quantile(oof, 1 - y.mean()), 0.01, 0.99)))


res = {}
for vn, cols in VARIANTES.items():
    X = matriz(datos, cols)
    for mn, (est, malla, paso) in MODELOS.items():
        prob = np.empty(len(y))
        for k in sorted(datos["fold"].unique()):
            tr, te = (datos["fold"] != k).to_numpy(), (datos["fold"] == k).to_numpy()
            b = GridSearchCV(clone(est), malla, scoring="f1_macro", cv=GroupKFold(5), n_jobs=2)
            b.fit(X[tr], y[tr], groups=g[tr], **kw(paso, y[tr]))
            d = desplazamiento(b.best_estimator_, paso, X[tr], y[tr], g[tr])
            p = b.best_estimator_.predict_proba(X[te])[:, 1]
            prob[te] = expit(logit(np.clip(p, 1e-6, 1 - 1e-6)) + d)
        oof = datos[["child_id", "figura_id", "edad_meses", "fold"]].assign(
            y=y, prob=prob, yhat=(prob >= 0.5).astype(float))
        oof.to_parquet(AQUI / f"processed/oof_crit_{vn}_{mn}.parquet")
        ev = evaluar_oof(oof, baremo, crit)
        pdn = oof.groupby("child_id").agg(r=("y", "sum"), p=("yhat", "sum"))
        res[f"{vn}|{mn}"] = {**resumen_corto(ev), "error_medio_PD": round(float((pdn.p - pdn.r).abs().mean()), 2),
                             "kappa_por_figura": {f: m.get("kappa") for f, m in ev["por_figura"]["por_figura"].items()}}
        print(vn, mn, json.dumps({k: v for k, v in res[f"{vn}|{mn}"].items() if k != "kappa_por_figura"}), flush=True)
json.dump({"resultados": res, "referencia_modelo": ref}, open(AQUI / "evaluacion_criterios.json", "w"), indent=2, default=float)
