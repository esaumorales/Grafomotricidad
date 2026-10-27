"""Calcula los indicadores de criterios2.py para las 1,545 figuras y su diferencia con la plantilla."""
import numpy as np, pandas as pd
from grafomotor.config import load_config
from grafomotor.io import a_binaria, leer_gris
from criterios2 import CLAVES, medir2

cfg = load_config("../config.yaml")
feat = pd.read_parquet("../processed/features.parquet")[["child_id", "figura_id"]]
ref = {f: medir2(a_binaria(leer_gris(cfg.ruta("templates") / f"{f}.png"))) for f in cfg.figuras}
filas = []
for r in feat.itertuples(index=False):
    p = cfg.ruta("interim") / f"{r.child_id}__{r.figura_id}.png"
    m = medir2(a_binaria(leer_gris(p))) if p.exists() else {k: np.nan for k in CLAVES}
    fila = {"child_id": r.child_id, "figura_id": r.figura_id}
    for k in CLAVES:
        fila[f"cr2_{k}"] = m[k]
        rv = ref[r.figura_id][k]
        fila[f"dif2_{k}"] = abs(m[k] - rv) if not (pd.isna(m[k]) or pd.isna(rv)) else np.nan
    filas.append(fila)
pd.DataFrame(filas).to_parquet("criterios2.parquet"); print("listo", len(filas))
