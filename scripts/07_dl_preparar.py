"""Modelo B: recortes 224x224 -> data/interim_dl/.

Envoltorio de `grafomotor preparar-dl` (lógica en src/grafomotor/comandos/). Opciones: --help
"""
import sys

from grafomotor.cli import ejecutar_comando

if __name__ == "__main__":
    sys.exit(ejecutar_comando("preparar-dl", sys.argv[1:]))
