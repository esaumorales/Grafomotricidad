"""Robustez de A y B (degradaciones y doble foto).

Envoltorio de `grafomotor robustez` (lógica en src/grafomotor/comandos/). Opciones: --help
"""
import sys

from grafomotor.cli import ejecutar_comando

if __name__ == "__main__":
    sys.exit(ejecutar_comando("robustez", sys.argv[1:]))
