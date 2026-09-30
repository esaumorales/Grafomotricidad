"""
Cadena completa. Envoltorio de `grafomotor todo` (lógica en src/grafomotor/comandos/todo.py).

  python run_all.py --sinteticos          plantillas + datos falsos + modelo A
  python run_all.py --sinteticos --dl     ... + modelo B y comparación A vs B
  python run_all.py --dl                  con los datos reales de data/
"""
import sys

from grafomotor.cli import ejecutar_comando

if __name__ == "__main__":
    sys.exit(ejecutar_comando("todo", sys.argv[1:]))
