"""Grad-CAM del modelo B.

Envoltorio de `grafomotor gradcam` (lógica en src/grafomotor/comandos/). Opciones: --help
"""
import sys

from grafomotor.cli import ejecutar_comando

if __name__ == "__main__":
    sys.exit(ejecutar_comando("gradcam", sys.argv[1:]))
