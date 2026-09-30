"""Modelo A: preprocesa las fotos -> data/interim/.

Envoltorio de `grafomotor preprocesar` (lógica en src/grafomotor/comandos/). Opciones: --help
"""
import sys

from grafomotor.cli import ejecutar_comando

if __name__ == "__main__":
    sys.exit(ejecutar_comando("preprocesar", sys.argv[1:]))
