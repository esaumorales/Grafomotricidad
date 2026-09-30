"""Modelo A vs una variante de B.

Envoltorio de `grafomotor comparar` (lógica en src/grafomotor/comandos/). Opciones: --help
"""
import sys

from grafomotor.cli import ejecutar_comando

if __name__ == "__main__":
    sys.exit(ejecutar_comando("comparar", sys.argv[1:]))
