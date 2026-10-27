"""Corrección del punto de corte de las redes (igual que en ML: corte por prevalencia).
Para cada fold k se usa SOLO el lado de entrenamiento: los niños de validación interna con que
la red eligió su mejor época (mismo GroupShuffleSplit y semilla que dl/entrenar.py). El corte es
el cuantil (1 - prevalencia de entrenamiento) de sus probabilidades; los niños de prueba del fold
k no intervienen. No se reentrena ninguna red."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score
from sklearn.model_selection import GroupShuffleSplit

from grafomotor.artefactos import Artefactos
from grafomotor.comandos.entrenar_dl import nombre_variante, tabla_de_entrenamiento
from grafomotor.config import load_config
from grafomotor.dl.entrenar import CONFIG_POR_DEFECTO, predecir
from grafomotor.dl.modelo import cargar
from grafomotor.evaluation.reporte import evaluar_oof, resumen_corto
from grafomotor.scoring.baremo import cargar_baremo
from grafomotor.scoring.niveles import CriterioNiveles

AQUI = Path(__file__).parent
cfg = load_config(AQUI / "config.yaml"); art = Artefactos.de_config(cfg)
cfg_dl = {**CONFIG_POR_DEFECTO, **dict(cfg.get("dl", default={}))}
lado = int(cfg_dl.get("lado_px", 224)); figuras = list(cfg.figuras)
df = tabla_de_entrenamiento(cfg, art, lado); medibles = df[df["dl_path"].notna()]
carpeta = art.carpeta_dl(lado)
baremo, crit = cargar_baremo(cfg.ruta("baremos")), CriterioNiveles.de_config(cfg)
rng = np.random.default_rng(20260930); res = {}
for arq in ["resnet18", "mobilenetv2", "efficientnet_b0"]:
    var = nombre_variante(arq, cfg_dl["aumento"], 0, lado)
    oof = pd.read_parquet(art.oof_dl(var)); cortes = {}
    for k in sorted(medibles["fold"].unique()):
        tr = medibles[medibles["fold"] != k]
        gss = GroupShuffleSplit(n_splits=1, test_size=cfg_dl["fraccion_validacion"], random_state=cfg_dl["semilla"])
        _, va_idx = next(gss.split(tr, groups=tr["child_id"]))
        modelo, _ = cargar(art.modelo_dl_fold(var, k), "cuda")
        p_va = predecir(modelo, tr.iloc[va_idx], carpeta, figuras)
        corte = float(np.clip(np.quantile(p_va, 1 - tr["puntaje"].mean()), 0.01, 0.99))
        cortes[int(k)] = round(corte, 3)
        m = oof["fold"] == k
        oof.loc[m, "yhat"] = (oof.loc[m, "prob"] >= corte).astype(float)
    oof.to_parquet(AQUI / f"processed/oof_dl_{arq}_corte.parquet")
    r = resumen_corto(evaluar_oof(oof, baremo, crit))
    pdn = oof.groupby("child_id").agg(r=("y", "sum"), p=("yhat", "sum"))
    ninos = oof.child_id.unique(); gr = {c: oof[oof.child_id == c] for c in ninos}; ks = []
    for _ in range(1000):
        mm = pd.concat([gr[c] for c in rng.choice(ninos, len(ninos))]); ks.append(cohen_kappa_score(mm.y, mm.yhat))
    res[arq] = {**r, "error_medio_PD": round(float((pdn.p - pdn.r).abs().mean()), 2),
                "kappa_IC95": [round(float(np.percentile(ks, 2.5)), 2), round(float(np.percentile(ks, 97.5)), 2)],
                "cortes_por_fold": cortes}
    print(arq, json.dumps(res[arq]), flush=True)
json.dump(res, open(AQUI / "evaluacion_dl_corte.json", "w"), indent=2)
