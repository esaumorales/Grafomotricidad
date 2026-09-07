"""Guardado/carga del artefacto del modelo + manifiesto (versión, fecha, métricas)."""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path

import joblib


@dataclass
class Manifiesto:
    creado: str
    git_hash: str
    feature_names: list[str]
    mejores_params: dict
    cv_f1_macro: float
    n_clases_nivel: int
    version_baremo: str
    notas: str = ""


def _git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                       text=True).strip()
    except Exception:
        return "sin-git"


def guardar_modelo(modelo, manifiesto: Manifiesto, carpeta: str | Path) -> Path:
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    joblib.dump(modelo, carpeta / "modelo_xgb.joblib")
    (carpeta / "manifiesto.json").write_text(
        json.dumps(asdict(manifiesto), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return carpeta


def cargar_modelo(carpeta: str | Path):
    carpeta = Path(carpeta)
    modelo = joblib.load(carpeta / "modelo_xgb.joblib")
    manifiesto = json.loads((carpeta / "manifiesto.json").read_text(encoding="utf-8"))
    return modelo, manifiesto


def nuevo_manifiesto(res, cfg) -> Manifiesto:
    return Manifiesto(
        creado=date.today().isoformat(),
        git_hash=_git_hash(),
        feature_names=res.feature_names,
        mejores_params=res.mejores_params,
        cv_f1_macro=round(res.cv_f1_macro, 4),
        n_clases_nivel=int(cfg.get("scoring", "n_clases", default=2)),
        version_baremo=str(cfg.get("scoring", "version_baremo", default="")),
    )
