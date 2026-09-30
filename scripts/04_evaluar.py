"""Modelo A: evaluación out-of-fold -> oof_ml.parquet.

Envoltorio de `grafomotor evaluar-ml` (lógica en src/grafomotor/comandos/). Opciones: --help
"""
import sys

from grafomotor.cli import ejecutar_comando

if __name__ == "__main__":
    sys.exit(ejecutar_comando("evaluar-ml", sys.argv[1:]))
