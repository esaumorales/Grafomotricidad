"""Probabilidad de EfficientNet-B0 para usarla como una variable más del Random Forest.
Sin fuga hacia la prueba final: dentro de los 83 niños de desarrollo, 5 pliegues por niño dan
una probabilidad fuera de pliegue para cada figura; para los 20 de prueba, una red entrenada
solo con los 83 de desarrollo."""
import numpy as np, pandas as pd, torch
from sklearn.model_selection import StratifiedGroupKFold
from grafomotor.artefactos import Artefactos
from grafomotor.comandos.entrenar_dl import tabla_de_entrenamiento
from grafomotor.config import load_config
from grafomotor.dl.entrenar import CONFIG_POR_DEFECTO, entrenar_fold, predecir

cfg = load_config("../config.yaml"); art = Artefactos.de_config(cfg)
cfg_dl = {**CONFIG_POR_DEFECTO, **dict(cfg.get("dl", default={})), "arquitectura": "efficientnet_b0"}
lado = int(cfg_dl.get("lado_px", 224)); figuras = list(cfg.figuras); carpeta = art.carpeta_dl(lado)
df = tabla_de_entrenamiento(cfg, art, lado)
ap = pd.read_csv("apartados.csv"); df = df.merge(ap, on="child_id")
dev, test = df[df.conjunto == "desarrollo"].copy(), df[df.conjunto == "prueba"].copy()
pdn = dev.groupby("child_id").puntaje.sum()
estr = dev.child_id.map(pd.qcut(pdn.rank(method="first"), 3, labels=False))
dev["pliegue"] = -1
for k, (_, te) in enumerate(StratifiedGroupKFold(5, shuffle=True, random_state=20261024).split(dev, estr, dev.child_id)):
    dev.iloc[te, dev.columns.get_loc("pliegue")] = k
dev["prob_red"] = np.nan
for k in range(5):
    tr, te = dev[dev.pliegue != k], dev[dev.pliegue == k]
    res = entrenar_fold(tr[tr.dl_path.notna()], carpeta, figuras, cfg_dl, verbose=False)
    m = te.dl_path.notna()
    dev.loc[te.index[m], "prob_red"] = predecir(res.modelo, te[m], carpeta, figuras)
    print("pliegue", k, "listo", flush=True); del res; torch.cuda.empty_cache()
res = entrenar_fold(dev[dev.dl_path.notna()], carpeta, figuras, cfg_dl, verbose=False)
m = test.dl_path.notna(); test["prob_red"] = np.nan; test["pliegue"] = -1
test.loc[test.index[m], "prob_red"] = predecir(res.modelo, test[m], carpeta, figuras)
torch.save(res.modelo.state_dict(), "red_final_desarrollo.pt")
out = pd.concat([dev, test])[["child_id", "figura_id", "conjunto", "pliegue", "prob_red"]]
out.to_parquet("prob_red.parquet"); print("listo", out.prob_red.notna().sum(), "de", len(out))
