"""Carga de configuración."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "config" / "config.yaml"


@dataclass
class Config:
    raw: dict[str, Any]

    # --- accesos cómodos ---
    @property
    def rutas(self) -> dict[str, Path]:
        return {k: (REPO_ROOT / v) for k, v in self.raw["rutas"].items()}

    def ruta(self, clave: str) -> Path:
        return REPO_ROOT / self.raw["rutas"][clave]

    @property
    def indicadores(self) -> list[str]:
        return list(self.raw["indicadores"]["usar"])

    @property
    def figuras(self) -> dict[str, dict]:
        return dict(self.raw["figuras"])

    def get(self, *path: str, default=None):
        node = self.raw
        for p in path:
            if not isinstance(node, dict) or p not in node:
                return default
            node = node[p]
        return node


def load_config(path: str | Path | None = None) -> Config:
    path = Path(path) if path else DEFAULT_CONFIG
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    return Config(raw=raw)
