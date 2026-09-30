"""Modelo A: entrena XGBoost -> models/actual/.

Envoltorio de `grafomotor entrenar-ml` (lógica en src/grafomotor/comandos/). Opciones: --help
"""
import sys

from grafomotor.cli import ejecutar_comando

if __name__ == "__main__":
    sys.exit(ejecutar_comando("entrenar-ml", sys.argv[1:]))
