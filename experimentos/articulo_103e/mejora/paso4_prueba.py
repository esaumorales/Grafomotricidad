"""Prueba final, una sola vez: V3 (elegida en desarrollo) y V0 (base) entrenadas con los 83 niños
de desarrollo y evaluadas con los 20 niños apartados. IC 95 % por bootstrap de niños (2000)."""
import json
import numpy as np, pandas as pd
from sklearn.metrics import cohen_kappa_score
from grafomotor.evaluation.metrics import icc_acuerdo_absoluto
from grafomotor.model.dataset import matriz
from paso3_evaluar import ajustar, construir_datos

d, C = construir_datos()
dev, test = d[d.conjunto == "desarrollo"].reset_index(drop=True), d[d.conjunto == "prueba"].reset_index(drop=True)
V = {"V0_base": (C["base"], False), "V3_elegida": (C["base"] + C["c2"] + ["prob_red"], True)}


def med(o):
    p = o.groupby("child_id").agg(r=("y", "sum"), q=("yhat", "sum"))
    return cohen_kappa_score(o.y, o.yhat), icc_acuerdo_absoluto(p.r, p.q), float((p.q - p.r).abs().mean())


rng = np.random.default_rng(20261024); ninos = test.child_id.unique()
muestras = [rng.choice(ninos, len(ninos)) for _ in range(2000)]
res, oofs = {}, {}
for n, (cols, cf) in V.items():
    Xd, yd = matriz(dev, cols), dev.puntaje.to_numpy().astype(int)
    m, corte, params = ajustar(Xd, yd, dev.child_id.to_numpy(), dev.figura_id.to_numpy(), cf)
    p = m.predict_proba(matriz(test, cols))[:, 1]
    o = test[["child_id", "figura_id"]].assign(y=test.puntaje.astype(int), prob=p,
                                               yhat=(p >= corte(p, test.figura_id.to_numpy())).astype(int))
    o.to_parquet(f"prueba_{n}.parquet"); oofs[n] = o
    g = {c: s for c, s in o.groupby("child_id")}
    b = np.array([med(pd.concat([g[c].assign(child_id=f"{c}#{i}") for i, c in enumerate(s)])) for s in muestras])
    k, cci, mae = med(o)
    ic = lambda j: [round(float(np.percentile(b[:, j], 2.5)), 3), round(float(np.percentile(b[:, j], 97.5)), 3)]  # noqa
    res[n] = {"params": params, "kappa": round(k, 3), "kappa_IC95": ic(0), "cci": round(cci, 3), "cci_IC95": ic(1),
              "error_PD": round(mae, 2), "error_IC95": ic(2),
              "kappa_fig": {f: round(cohen_kappa_score(s.y, s.yhat), 2) for f, s in o.groupby("figura_id")}}
    print(n, json.dumps({k2: v for k2, v in res[n].items() if k2 != "kappa_fig"}), flush=True)
a, b0 = oofs["V3_elegida"], oofs["V0_base"]
ga, gb = {c: s for c, s in a.groupby("child_id")}, {c: s for c, s in b0.groupby("child_id")}
dk = [cohen_kappa_score(*(lambda m: (m.y, m.yhat))(pd.concat([ga[c] for c in s]))) -
      cohen_kappa_score(*(lambda m: (m.y, m.yhat))(pd.concat([gb[c] for c in s]))) for s in muestras]
res["diferencia_kappa_V3_menos_V0"] = {"d": round(res["V3_elegida"]["kappa"] - res["V0_base"]["kappa"], 3),
                                        "IC95": [round(float(np.percentile(dk, 2.5)), 3), round(float(np.percentile(dk, 97.5)), 3)]}
print(res["diferencia_kappa_V3_menos_V0"])
json.dump(res, open("evaluacion_prueba_final.json", "w"), indent=2)
