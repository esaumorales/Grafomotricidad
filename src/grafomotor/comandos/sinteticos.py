"""Paso 99: dataset sintético para probar la cadena sin datos reales."""
from __future__ import annotations

import argparse

from grafomotor.config import Config
from grafomotor.datos.sinteticos import ParametrosSinteticos, generar_dataset

AYUDA = "genera fotos y etiquetas SINTÉTICAS (solo para probar el código)"


def agregar_argumentos(p: argparse.ArgumentParser) -> None:
    p.add_argument("--n-ninos", type=int, default=ParametrosSinteticos.n_ninos)
    p.add_argument("--semilla", type=int, default=ParametrosSinteticos.semilla)
    p.add_argument("--fraccion-doble", type=float, default=ParametrosSinteticos.fraccion_doble,
                   help="fracción de niños con un 2.º evaluador simulado")


def ejecutar(args: argparse.Namespace, cfg: Config) -> int:
    generar_dataset(cfg, ParametrosSinteticos(args.n_ninos, args.semilla, args.fraccion_doble))
    return 0
