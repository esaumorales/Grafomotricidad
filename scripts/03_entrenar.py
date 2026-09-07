"""Entrena XGBoost (puntaje por figura), CV agrupada por niño, y guarda el artefacto."""
from __future__ import annotations

import json
import sys

import pandas as pd

from grafomotor.config import load_config
from grafomotor.io import cargar_etiquetas
from grafomotor.model.dataset import construir
from grafomotor.model.registry import guardar_modelo, nuevo_manifiesto
from grafomotor.model.train import entrenar


def main() -> int:
    cfg = load_config()
    features = pd.read_parquet(cfg.ruta("processed") / "features.parquet")
    etiquetas = cargar_etiquetas(cfg.ruta("labels"))
    datos = construir(features, etiquetas)

    print(f"n={len(datos.y)} figuras · {len(set(datos.grupos))} niños · "
          f"tasa acierto={datos.y.mean():.3f}")
    res = entrenar(datos, cfg.get("modelo", default={}))
    print("mejores params:", json.dumps(res.mejores_params, indent=2))
    print(f"F1 macro (CV agrupada por niño): {res.cv_f1_macro:.3f}  folds={res.cv_f1_por_fold}")

    carpeta = cfg.ruta("models") / "actual"
    guardar_modelo(res.modelo, nuevo_manifiesto(res, cfg), carpeta)
    print(f"modelo -> {carpeta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
