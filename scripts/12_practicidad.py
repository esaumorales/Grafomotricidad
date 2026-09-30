"""Pasos, segundos por hoja y fallos de A y B.

Envoltorio de `grafomotor practicidad` (lógica en src/grafomotor/comandos/). Opciones: --help
"""
import sys

from grafomotor.cli import ejecutar_comando

if __name__ == "__main__":
    sys.exit(ejecutar_comando("practicidad", sys.argv[1:]))
