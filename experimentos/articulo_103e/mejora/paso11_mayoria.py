"""Sensibilidad con las etiquetas por mayoría (Experimento_103d/etiquetas.csv) sobre el procesamiento corregido (103e):
Random Forest entrenado con las notas originales y con las de mayoría. Copia de 103d/mejora/paso11 con las rutas de 103e."""
import json

import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score, f1_score, recall_score

from grafomotor.evaluation.metrics import icc_acuerdo_absoluto
from grafomotor.model.dataset import matriz
from paso3_evaluar import ajustar, construir_datos

d, C = construir_datos()
d = d.merge(pd.read_csv("../processed/particiones.csv"), on="child_id")
mayoria = pd.read_csv("D:/Datos niños/Experimento_103d/etiquetas.csv")[["child_id", "figura_id", "puntaje"]].rename(columns={"puntaje": "y_mayoria"})
d = d.merge(mayoria, on=["child_id", "figura_id"]).rename(columns={"puntaje": "y_vieja"}).rename(columns={"y_mayoria": "puntaje"})
print("figuras:", len(d), "| etiquetas distintas de la original:", int((d.puntaje != d.y_vieja).sum()))


def medidas(y, yhat, ninos):
    t = pd.DataFrame({"c": ninos, "y": y, "p": yhat}).groupby("c").sum()
    return {"exactitud_balanceada": round(balanced_accuracy_score(y, yhat), 3), "sensibilidad": round(recall_score(y, yhat), 3),
            "especificidad": round(recall_score(y, yhat, pos_label=0), 3), "f1_macro": round(f1_score(y, yhat, average="macro"), 3),
            "cci_PD": round(icc_acuerdo_absoluto(t.y, t.p), 3), "error_PD": round(float((t.p - t.y).abs().mean()), 2)}


def cv(col_y):
    X, y = matriz(d, C["base"]), d[col_y].to_numpy().astype(int)
    g, fig = d.child_id.to_numpy(), d.figura_id.to_numpy()
    yhat = np.empty(len(y))
    for k in sorted(d.fold.unique()):
        tr, te = (d.fold != k).to_numpy(), (d.fold == k).to_numpy()
        m, corte, _ = ajustar(X[tr], y[tr], g[tr], fig[tr], False)
        p = m.predict_proba(X[te])[:, 1]
        yhat[te] = (p >= corte(p, fig[te])).astype(int)
    return yhat


res = {"A_validacion_cruzada_103": {}, "B_prueba_20": {}}
yv, yn = d.y_vieja.to_numpy().astype(int), d.puntaje.to_numpy().astype(int)
for nombre, col in (("entrenado_notas_originales", "y_vieja"), ("entrenado_notas_mayoria", "puntaje")):
    yhat = cv(col)
    res["A_validacion_cruzada_103"][nombre] = {"contra_original": medidas(yv, yhat, d.child_id), "contra_mayoria": medidas(yn, yhat, d.child_id)}
    print("A", nombre, res["A_validacion_cruzada_103"][nombre], flush=True)

dev, test = d[d.conjunto == "desarrollo"], d[d.conjunto == "prueba"]
for nombre, col in (("entrenado_notas_originales", "y_vieja"), ("entrenado_notas_mayoria", "puntaje")):
    m, corte, _ = ajustar(matriz(dev, C["base"]), dev[col].to_numpy().astype(int), dev.child_id.to_numpy(), dev.figura_id.to_numpy(), False)
    p = m.predict_proba(matriz(test, C["base"]))[:, 1]
    yhat = (p >= corte(p, test.figura_id.to_numpy())).astype(int)
    res["B_prueba_20"][nombre] = {"contra_original": medidas(test.y_vieja.to_numpy().astype(int), yhat, test.child_id),
                                  "contra_mayoria": medidas(test.puntaje.to_numpy().astype(int), yhat, test.child_id)}
    print("B", nombre, res["B_prueba_20"][nombre], flush=True)
json.dump(res, open("evaluacion_mayoria_103e.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
