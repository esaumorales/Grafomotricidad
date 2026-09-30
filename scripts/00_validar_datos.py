"""Valida data/labels/etiquetas.csv y resume el dataset.

Envoltorio de `grafomotor validar` (lógica en src/grafomotor/comandos/). Opciones: --help
"""
import sys

from grafomotor.cli import ejecutar_comando

if __name__ == "__main__":
    sys.exit(ejecutar_comando("validar", sys.argv[1:]))
