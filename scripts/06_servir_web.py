"""App web del docente en http://127.0.0.1:8000.

Envoltorio de `grafomotor servir` (lógica en src/grafomotor/comandos/). Opciones: --help
"""
import sys

from grafomotor.cli import ejecutar_comando

if __name__ == "__main__":
    sys.exit(ejecutar_comando("servir", sys.argv[1:]))
