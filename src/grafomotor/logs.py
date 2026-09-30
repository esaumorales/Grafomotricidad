"""Logging del proyecto: un solo formato para todos los comandos."""
from __future__ import annotations

import logging
import sys

FORMATO = "%(asctime)s  %(levelname)-7s  %(name)s: %(message)s"
FORMATO_FECHA = "%H:%M:%S"


def configurar_logs(nivel: int | str = logging.INFO) -> None:
    """Configura el logger raíz del paquete (idempotente). Lo llama el CLI al arrancar."""
    raiz = logging.getLogger("grafomotor")
    raiz.setLevel(nivel)
    if not raiz.handlers:
        h = logging.StreamHandler(sys.stderr)
        h.setFormatter(logging.Formatter(FORMATO, FORMATO_FECHA))
        raiz.addHandler(h)
    raiz.propagate = False


def obtener_logger(nombre: str) -> logging.Logger:
    """`obtener_logger(__name__)` en cada módulo."""
    return logging.getLogger(nombre if nombre.startswith("grafomotor") else f"grafomotor.{nombre}")
