"""Plantillas vectoriales de las 15 figuras.

Envoltorio de `grafomotor plantillas` (lógica en src/grafomotor/comandos/). Opciones: --help
"""
import sys

from grafomotor.cli import ejecutar_comando

if __name__ == "__main__":
    sys.exit(ejecutar_comando("plantillas", sys.argv[1:]))
