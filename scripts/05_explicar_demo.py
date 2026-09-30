"""Informe para el docente (real con --child-id o --simular).

Envoltorio de `grafomotor explicar` (lógica en src/grafomotor/comandos/). Opciones: --help
"""
import sys

from grafomotor.cli import ejecutar_comando

if __name__ == "__main__":
    sys.exit(ejecutar_comando("explicar", sys.argv[1:]))
