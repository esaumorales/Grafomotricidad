"""Modelo A: 6 indicadores -> features.parquet.

Envoltorio de `grafomotor extraer-features` (lógica en src/grafomotor/comandos/). Opciones: --help
"""
import sys

from grafomotor.cli import ejecutar_comando

if __name__ == "__main__":
    sys.exit(ejecutar_comando("extraer-features", sys.argv[1:]))
