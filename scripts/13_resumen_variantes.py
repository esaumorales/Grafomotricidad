"""Todas las variantes de B frente a A.

Envoltorio de `grafomotor resumen-variantes` (lógica en src/grafomotor/comandos/). Opciones: --help
"""
import sys

from grafomotor.cli import ejecutar_comando

if __name__ == "__main__":
    sys.exit(ejecutar_comando("resumen-variantes", sys.argv[1:]))
