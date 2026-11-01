"""V5: el modelo final (V0) con el indicador "error angular" SOLO en las figuras donde la Tabla S1 lo
asigna a un criterio del manual (F01, F04, F05, F07, F15). En las demás figuras sus tres columnas
(error_angular, raw_error_angular_deg, dif_angulo) se dejan vacías (NaN) y las rellena el imputador,
que además marca 'faltaba este dato'.

Motivo (análisis añadido después de la selección de modelos, 01/11): en la RQ3 el error angular fue el
indicador con mayor aporte SHAP en 389 de 672 figuras calificadas como incorrectas, también en figuras
curvas donde el manual no revisa ángulos. En desarrollo (83 niños, mismos pliegues) V5 dio kappa 0,556
frente a 0,539 de V0. Este script:
  1) repite la evaluación en desarrollo y guarda las probabilidades fuera de pliegue;
  2) fija los límites de la revisión por confianza con desarrollo (misma regla que paso5);
  3) evalúa una vez con los 20 niños de prueba (IC 95 % por bootstrap de niños, misma semilla que paso4)
     y la diferencia con V0;
  4) guarda los modelos modelo_rf_103h_83_ea y modelo_rf_103h_103_ea (no toca los de paso12);
  5) comprueba que grafomotor.model.final (la app), desde las imágenes procesadas, da las mismas
     probabilidades.
No modifica ningún script ni archivo anterior."""
import json
import sys
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import cohen_kappa_score as K

from grafomotor.evaluation.metrics import icc_acuerdo_absoluto
from grafomotor.io import a_binaria, cargar_plantillas, leer_gris
from grafomotor.model.dataset import matriz
from paso3_evaluar import ajustar, cfg, construir_datos, medidas, variante

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from criterios import medir  # noqa: E402

SAL = Path(__file__).resolve().parents[1] / "modelos"
EA = ["error_angular", "raw_error_angular_deg", "dif_angulo"]
CON_EA = ["F01", "F04", "F05", "F07", "F15"]  # Tabla S1: figuras con "Error angular" en algún criterio


def enmascarar(d: pd.DataFrame) -> pd.DataFrame:
    d = d.copy()
    d.loc[~d.figura_id.isin(CON_EA), EA] = np.nan
    return d


d0, C = construir_datos()
cols = C["base"]
d = enmascarar(d0)
dev = d[d.conjunto == "desarrollo"].reset_index(drop=True)
test = d[d.conjunto == "prueba"].reset_index(drop=True)
res = {"columnas_anuladas": EA, "solo_en_figuras": CON_EA}

# 1) desarrollo -------------------------------------------------------------------------------- #
o_dev = variante(dev, cols, False, False)
o_dev.to_parquet("oof_dev_V5_ea_por_figura.parquet")
res["desarrollo"] = {"V5": medidas(o_dev), "V0": medidas(pd.read_parquet("oof_dev_V0_base.parquet"))}
print("desarrollo V5", {k: v for k, v in res["desarrollo"]["V5"].items() if k != "kappa_fig"}, flush=True)
print("desarrollo V0", {k: v for k, v in res["desarrollo"]["V0"].items() if k != "kappa_fig"}, flush=True)

# 2) límites de confianza (regla de paso5, con desarrollo) ------------------------------------- #
OBJ = 0.90


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


li, ls = limites(o_dev)


def confianza(o):
    seg = (o.prob <= li) | (o.prob >= ls)
    auto = o[seg].assign(nota=lambda x: (x.prob >= ls).astype(int))
    rev = o[~seg]
    final = pd.concat([auto, rev.assign(nota=rev.y)])
    p = final.groupby("child_id").agg(r=("y", "sum"), q=("nota", "sum"))
    return {"cobertura_automatica_%": round(100 * seg.mean(), 1),
            "figuras_a_revisar_por_nino": round((~seg).sum() / o.child_id.nunique(), 1),
            "acierto_automaticas_%": round(100 * (auto.nota == auto.y).mean(), 1),
            "kappa_automaticas": round(K(auto.y, auto.nota), 3),
            "kappa_final_con_revision": round(K(final.y, final.nota), 3),
            "cci_PD_final": round(icc_acuerdo_absoluto(p.r, p.q), 3),
            "error_PD_final": round(float((p.q - p.r).abs().mean()), 2)}


res["limites"] = {"a_incorrecta": li, "b_correcta": ls}
res["confianza_desarrollo"] = confianza(o_dev)
print("límites", li, ls, res["confianza_desarrollo"], flush=True)

# 3) prueba única con los 20 niños (como paso4) ------------------------------------------------ #
Xd, yd = matriz(dev, cols), dev.puntaje.to_numpy().astype(int)
m83, corte83, params83 = ajustar(Xd, yd, dev.child_id.to_numpy(), dev.figura_id.to_numpy(), False)
p = m83.predict_proba(matriz(test, cols))[:, 1]
o = test[["child_id", "figura_id"]].assign(y=test.puntaje.astype(int), prob=p,
                                           yhat=(p >= corte83(p, test.figura_id.to_numpy())).astype(int))
o.to_parquet("prueba_V5_ea_por_figura.parquet")
o0 = pd.read_parquet("prueba_V0_base.parquet")


def med(x):
    q = x.groupby("child_id").agg(r=("y", "sum"), q=("yhat", "sum"))
    return K(x.y, x.yhat), icc_acuerdo_absoluto(q.r, q.q), float((q.q - q.r).abs().mean())


rng = np.random.default_rng(20261024); ninos = test.child_id.unique()
muestras = [rng.choice(ninos, len(ninos)) for _ in range(2000)]
g, g0 = {c: s for c, s in o.groupby("child_id")}, {c: s for c, s in o0.groupby("child_id")}
b = np.array([med(pd.concat([g[c].assign(child_id=f"{c}#{i}") for i, c in enumerate(s)])) for s in muestras])
ic = lambda j: [round(float(np.percentile(b[:, j], 2.5)), 3), round(float(np.percentile(b[:, j], 97.5)), 3)]  # noqa
k, cci, mae = med(o)
dk = [K(*(lambda m: (m.y, m.yhat))(pd.concat([g[c] for c in s]))) -
      K(*(lambda m: (m.y, m.yhat))(pd.concat([g0[c] for c in s]))) for s in muestras]
res["prueba"] = {"params": params83, "kappa": round(k, 3), "kappa_IC95": ic(0), "cci": round(cci, 3),
                 "cci_IC95": ic(1), "error_PD": round(mae, 2), "error_IC95": ic(2),
                 "acierto_%": round(100 * float((o.y == o.yhat).mean()), 1),
                 "kappa_fig": {f: round(K(s.y, s.yhat), 2) for f, s in o.groupby("figura_id")},
                 "diferencia_kappa_V5_menos_V0": {"d": round(k - K(o0.y, o0.yhat), 3),
                                                  "IC95": [round(float(np.percentile(dk, 2.5)), 3),
                                                           round(float(np.percentile(dk, 97.5)), 3)]},
                 "confianza": confianza(o)}
print("prueba V5", {k2: v for k2, v in res["prueba"].items() if k2 != "kappa_fig"}, flush=True)

# 4) guardar modelos --------------------------------------------------------------------------- #
ref = {f: {kk: (None if v is None or (isinstance(v, float) and np.isnan(v)) else float(v))
           for kk, v in medir(a_binaria(leer_gris(cfg.ruta("templates") / f"{f}.png"))).items()}
       for f in cfg.figuras}


def guardar(datos, nombre, descripcion, ajuste=None):
    X, y = matriz(datos, cols), datos.puntaje.to_numpy().astype(int)
    m, corte, params = ajuste or ajustar(X, y, datos.child_id.to_numpy(), datos.figura_id.to_numpy(), False)
    c = float(corte(np.array([0.5]), np.array(["F01"]))[0])
    carpeta = SAL / nombre; carpeta.mkdir(parents=True, exist_ok=True)
    joblib.dump(m, carpeta / "modelo.joblib")
    man = {"version": nombre, "descripcion": descripcion, "fecha": date.today().isoformat(),
           "n_ninos": int(datos.child_id.nunique()), "n_figuras": int(len(datos)),
           "feature_names": cols, "punto_de_corte": c,
           "columnas_solo_en_figuras": {"columnas": EA, "figuras": CON_EA},
           "limites_confianza": {"incorrecta_si_prob_menor_o_igual": li, "correcta_si_prob_mayor_o_igual": ls},
           "hiperparametros": {kk: (None if v is None else v) for kk, v in params.items()},
           "figuras": list(cfg.figuras), "criterios_plantilla": ref,
           "entrada": "figura binaria 512 px de preprocesar_figura (registro: traslación); "
                      "ver grafomotor.model.final (anula columnas_solo_en_figuras fuera de esas figuras)",
           "versiones": {"python": sys.version.split()[0], "scikit-learn": sklearn.__version__}}
    (carpeta / "manifiesto.json").write_text(json.dumps(man, indent=2, ensure_ascii=False), encoding="utf-8")
    print(nombre, "corte", round(c, 4), params, flush=True)
    return m, c


guardar(dev, "modelo_rf_103h_83_ea", "V5 entrenado con los 83 niños de desarrollo; los 20 apartados no se usaron.",
        (m83, corte83, params83))
_, c103 = guardar(d, "modelo_rf_103h_103_ea", "V5 entrenado con los 103 niños (uso real en la aplicación).")
res["modelo_103"] = {"punto_de_corte": c103}

# 5) comprobación con la app desde las imágenes ------------------------------------------------ #
from grafomotor.model.final import ModeloFinal  # noqa: E402

mf = ModeloFinal(SAL / "modelo_rf_103h_83_ea")
plantillas = cargar_plantillas(cfg)
interim = Path(cfg.ruta("interim")); dif = []
for r in o[o.child_id.isin(o.child_id.unique()[:5])].itertuples():
    bi = a_binaria(leer_gris(interim / f"{r.child_id}__{r.figura_id}.png"))
    q = mf.predecir(bi, r.figura_id, plantillas[r.figura_id], cfg.figuras[r.figura_id])["prob"]
    dif.append(abs(q - r.prob))
res["comprobacion_app_max_dif"] = float(max(dif))
print("comprobación app, máx. diferencia desde la imagen:", float(max(dif)), "en", len(dif), "figuras", flush=True)
json.dump(res, open("evaluacion_V5_ea_por_figura.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
