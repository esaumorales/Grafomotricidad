"""Calificación con revisión por confianza. Regla fijada antes de mirar la prueba:
con las predicciones fuera de pliegue de los 83 niños de desarrollo (V3) se eligen dos límites,
a (seguro de incorrecta: prob <= a) y b (seguro de correcta: prob >= b), los más amplios en que
el acierto en desarrollo es >= 90 %. Las demás figuras van a revisión del docente.
Luego se aplican, sin cambiarlos, a los 20 niños de prueba."""
import json
import numpy as np, pandas as pd
from sklearn.metrics import cohen_kappa_score as K
from grafomotor.evaluation.metrics import icc_acuerdo_absoluto

OBJ = 0.90
dev = pd.read_parquet("oof_dev_V0_base.parquet"); test = pd.read_parquet("prueba_V0_base.parquet")


def limites(o):
    a_best = 0.0
    for a in np.arange(0.05, 0.50, 0.01):
        s = o[o.prob <= a]
        if len(s) >= 20 and (s.y == 0).mean() >= OBJ: a_best = a
    b_best = 1.0
    for b in np.arange(0.95, 0.50, -0.01):
        s = o[o.prob >= b]
        if len(s) >= 20 and (s.y == 1).mean() >= OBJ: b_best = b
    return round(float(a_best), 2), round(float(b_best), 2)


a, b = limites(dev)


def evaluar(o, nombre):
    seg = (o.prob <= a) | (o.prob >= b)
    auto = o[seg].assign(nota=lambda x: (x.prob >= b).astype(int))
    rev = o[~seg]
    # si el docente corrige las dudosas, la nota final = nota del modelo en las seguras + nota real en las dudosas
    final = pd.concat([auto, rev.assign(nota=rev.y)])
    p = final.groupby("child_id").agg(r=("y", "sum"), q=("nota", "sum"))
    r = {"cobertura_automatica_%": round(100 * seg.mean(), 1), "figuras_a_revisar_por_nino": round((~seg).sum() / o.child_id.nunique(), 1),
         "acierto_automaticas_%": round(100 * (auto.nota == auto.y).mean(), 1),
         "kappa_automaticas": round(K(auto.y, auto.nota), 3),
         "kappa_final_con_revision": round(K(final.y, final.nota), 3),
         "cci_PD_final": round(icc_acuerdo_absoluto(p.r, p.q), 3), "error_PD_final": round(float((p.q - p.r).abs().mean()), 2),
         "por_figura_cobertura_%": {f: round(100 * ((g.prob <= a) | (g.prob >= b)).mean()) for f, g in o.groupby("figura_id")}}
    print(nombre, json.dumps({k: v for k, v in r.items() if not k.startswith("por_")}, ensure_ascii=False))
    return r


res = {"limites": {"a_incorrecta": a, "b_correcta": b}, "desarrollo": evaluar(dev, "desarrollo"), "prueba": evaluar(test, "prueba")}
print("límites:", a, b); print("cobertura por figura (prueba):", res["prueba"]["por_figura_cobertura_%"])
json.dump(res, open("evaluacion_confianza_V0.json", "w"), indent=2, ensure_ascii=False)
