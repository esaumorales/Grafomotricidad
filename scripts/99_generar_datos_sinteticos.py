"""Dataset SINTÉTICO para probar la cadena.

Envoltorio de `grafomotor sinteticos` (lógica en src/grafomotor/comandos/). Opciones: --help
"""
import sys

from grafomotor.cli import ejecutar_comando

if __name__ == "__main__":
    sys.exit(ejecutar_comando("sinteticos", sys.argv[1:]))
