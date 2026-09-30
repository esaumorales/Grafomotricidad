"""Genera las plantillas vectoriales de las 15 figuras en data/templates/."""
from __future__ import annotations

import argparse

from grafomotor.config import Config
from grafomotor.datos.plantillas import generar_plantillas

AYUDA = "genera las plantillas de referencia de las 15 figuras (data/templates/)"


def agregar_argumentos(p: argparse.ArgumentParser) -> None:
    pass


def ejecutar(args: argparse.Namespace, cfg: Config) -> int:
    generar_plantillas(cfg)
    return 0
