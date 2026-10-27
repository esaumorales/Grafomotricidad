"""Resumen de los 6 modelos con las métricas de la literatura parecida (sin kappa).

Por figura: exactitud balanceada (principal para elegir el modelo), sensibilidad, especificidad,
F1 macro y exactitud. Por niño: CCI(A,1) y error absoluto medio de la PD. Nivel (68 niños con edad
en meses): exactitud, sensibilidad y especificidad para detectar "En riesgo".
IC 95 %: bootstrap de 2000 réplicas por niño (mismas réplicas y semilla que resumen_final.py);
diferencias con bootstrap pareado por niño frente al modelo de mayor exactitud balanceada.
También: ablación, métricas por figura, los 20 niños de prueba y la revisión por confianza."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, recall_score

from grafomotor.config import load_config
from grafomotor.evaluation.metrics import icc_acuerdo_absoluto
from grafomotor.evaluation.reporte import tabla_por_nino
from grafomotor.scoring.baremo import cargar_baremo
from grafomotor.scoring.niveles import CriterioNiveles

AQUI = Path(__file__).parent
PRO = AQUI / "processed"
MEJ = AQUI / "mejora"
cfg = load_config(AQUI / "config.yaml")
baremo, crit = cargar_baremo(cfg.ruta("baremos")), CriterioNiveles.de_config(cfg)
part = pd.read_csv(AQUI / "participantes_103.csv")
con_meses = set(part.loc[part["edad_meses"].notna(), "child_id"])
edad = dict(zip(part.child_id, part.edad_meses))
N_BOOT, SEM = 2000, 20260930

MODELOS = {
    "Regresión logística": "oof_crit_con_criterios_sin_proporcion_reg_logistica",
    "Random Forest": "oof_crit_con_criterios_sin_proporcion_random_forest",
    "XGBoost": "oof_crit_con_criterios_sin_proporcion_xgboost",
    "ResNet-18": "oof_dl_resnet18_corte",
    "MobileNetV2": "oof_dl_mobilenetv2_corte",
    "EfficientNet-B0": "oof_dl_efficientnet_b0_corte",
}


def r3(x):
    return round(float(x), 3)


def ic(v):
    return [r3(np.percentile(v, 2.5)), r3(np.percentile(v, 97.5))]


def por_figura(o):
    y, p = o.y.astype(int), o.yhat.fillna(0).astype(int)
    return {"exactitud_balanceada": balanced_accuracy_score(y, p), "sensibilidad": recall_score(y, p, pos_label=1),
            "especificidad": recall_score(y, p, pos_label=0), "f1_macro": f1_score(y, p, average="macro"),
            "exactitud": accuracy_score(y, p)}


def por_nino(o):
    pdn = o.assign(yhat=o.yhat.fillna(0)).groupby("child_id").agg(real=("y", "sum"), pred=("yhat", "sum"))
    return {"cci_PD": icc_acuerdo_absoluto(pdn.real, pdn.pred), "error_medio_PD": float((pdn.pred - pdn.real).abs().mean())}


def medidas(o):
    return {**por_figura(o), **por_nino(o)}


def nivel(o):
    sub = o[o.child_id.isin(con_meses)].copy()
    if "edad_meses" not in sub:
        sub["edad_meses"] = sub.child_id.map(edad)
    t = tabla_por_nino(sub, baremo, crit)
    r, m = t.nivel_completa_experto.eq("En riesgo"), t.nivel_completa_modelo.eq("En riesgo")
    return {"n_ninos": len(t), "n_en_riesgo_referencia": int(r.sum()), "n_en_riesgo_modelo": int(m.sum()),
            "detectados": int((r & m).sum()), "exactitud": r3((r == m).mean()),
            "sensibilidad_riesgo": r3((r & m).sum() / r.sum()) if r.sum() else None,
            "especificidad_riesgo": r3((~r & ~m).sum() / (~r).sum()) if (~r).sum() else None}


def boot(o, muestras, fn=medidas):
    g = {c: x for c, x in o.groupby("child_id")}
    out = {}
    for s in muestras:
        mm = pd.concat([g[c].assign(child_id=f"{c}#{i}") for i, c in enumerate(s)])
        for k, v in fn(mm).items():
            out.setdefault(k, []).append(v)
    return {k: np.array(v) for k, v in out.items()}


oofs = {m: pd.read_parquet(PRO / f"{a}.parquet") for m, a in MODELOS.items()}
ninos = sorted(next(iter(oofs.values())).child_id.unique())
rng = np.random.default_rng(SEM)
muestras = [rng.choice(ninos, len(ninos)) for _ in range(N_BOOT)]

res, boots = {}, {}
for m, o in oofs.items():
    v = medidas(o)
    boots[m] = boot(o, muestras)
    res[m] = {k: r3(x) for k, x in v.items()}
    res[m].update({f"{k}_IC95": ic(boots[m][k]) for k in v})
    res[m]["nivel"] = nivel(o)
    res[m]["por_figura"] = {f: {k: r3(x) for k, x in por_figura(g).items()} for f, g in o.groupby("figura_id")}
    print(m, json.dumps({k: x for k, x in res[m].items() if k != "por_figura"}, ensure_ascii=False), flush=True)

mejor = max(res, key=lambda m: res[m]["exactitud_balanceada"])
dif = {}
for m in res:
    if m == mejor:
        continue
    fila = {}
    for k in ("exactitud_balanceada", "cci_PD", "error_medio_PD"):
        d = boots[mejor][k] - boots[m][k]
        fila[k] = {"d": r3(res[mejor][k] - res[m][k]), "IC95": ic(d)}
    dif[f"{mejor} - {m}"] = fila

abl = {}
for mn in ("reg_logistica", "random_forest", "xgboost"):
    o3 = {v: pd.read_parquet(PRO / f"oof_crit_{v}_{mn}.parquet") for v in ("antes", "con_criterios", "con_criterios_sin_proporcion")}
    fila = {v: {k: r3(x) for k, x in medidas(o).items()} for v, o in o3.items()}
    b_fin, b_ant = boot(o3["con_criterios_sin_proporcion"], muestras), boot(o3["antes"], muestras)
    fila["mejora"] = {k: {"d": r3(fila["con_criterios_sin_proporcion"][k] - fila["antes"][k]), "IC95": ic(b_fin[k] - b_ant[k])}
                      for k in ("exactitud_balanceada", "cci_PD", "error_medio_PD")}
    abl[mn] = fila
    print("ablación", mn, json.dumps(fila["mejora"]), flush=True)

# 20 niños de prueba (V0 = Random Forest base, entrenado con los 83 de desarrollo)
pr = pd.read_parquet(MEJ / "prueba_V0_base.parquet")
n20 = sorted(pr.child_id.unique())
rng20 = np.random.default_rng(SEM)
m20 = [rng20.choice(n20, len(n20)) for _ in range(N_BOOT)]
b20 = boot(pr, m20)
prueba = {k: r3(x) for k, x in medidas(pr).items()}
prueba.update({f"{k}_IC95": ic(b20[k]) for k in prueba})

# revisión por confianza en los 20 (límites elegidos en desarrollo, paso5_confianza_V0.py)
_lim = json.load(open(MEJ / "evaluacion_confianza_V0.json"))["limites"]
A, B = _lim["a_incorrecta"], _lim["b_correcta"]


def confianza(o):
    auto = (o.prob <= A) | (o.prob >= B)
    oa = o[auto]
    fin = o.assign(yhat=np.where(auto, o.yhat, o.y))  # supuesto: el docente califica como la referencia
    return {"cobertura": auto.mean(), "acierto_auto": accuracy_score(oa.y, oa.yhat),
            "exact_bal_auto": balanced_accuracy_score(oa.y, oa.yhat), "revisar_por_nino": (~auto).sum() / o.child_id.nunique(),
            **{f"final_{k}": x for k, x in por_nino(fin).items()}}


bc = boot(pr, m20, confianza)
conf = {k: r3(x) for k, x in confianza(pr).items()}
conf.update({f"{k}_IC95": ic(bc[k]) for k in conf})
conf["limites"] = [A, B]

json.dump({"n_ninos": len(ninos), "modelos": res, "mejor": mejor, "diferencias": dif, "ablacion": abl,
           "prueba_20": prueba, "confianza_20": conf},
          open(AQUI / "resultados_sin_kappa.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2, default=float)
print("mejor", mejor)
print("diferencias", json.dumps(dif, ensure_ascii=False))
print("prueba", json.dumps(prueba))
print("confianza", json.dumps(conf))
