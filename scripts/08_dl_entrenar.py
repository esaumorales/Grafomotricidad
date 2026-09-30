"""Modelo B: entrena la red por fold (ver --help).

Envoltorio de `grafomotor entrenar-dl` (lógica en src/grafomotor/comandos/). Opciones: --help
"""
import sys

from grafomotor.cli import ejecutar_comando

if __name__ == "__main__":
    sys.exit(ejecutar_comando("entrenar-dl", sys.argv[1:]))
