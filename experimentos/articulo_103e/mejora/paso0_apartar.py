"""Aparta 20 niños como prueba final ANTES de cualquier mejora. Estratificado por tercil de la
PD de referencia para que la prueba tenga niños con PD baja, media y alta. Semilla fija."""
import numpy as np, pandas as pd
e = pd.read_csv("../etiquetas.csv")
pd_n = e.groupby("child_id").puntaje.sum()
terc = pd.qcut(pd_n.rank(method="first"), 3, labels=False)
rng = np.random.default_rng(20261024)
cuotas = {0: 7, 1: 7, 2: 6}
prueba = sorted(c for t, k in cuotas.items() for c in rng.choice(terc[terc == t].index, k, replace=False))
pd.DataFrame({"child_id": pd_n.index, "conjunto": ["prueba" if c in prueba else "desarrollo" for c in pd_n.index]}).to_csv("apartados.csv", index=False)
print("prueba:", prueba)
print("PD media prueba", round(pd_n[prueba].mean(), 2), "| desarrollo", round(pd_n.drop(prueba).mean(), 2))
