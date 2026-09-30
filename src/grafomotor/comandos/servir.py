"""Paso 06: levanta la API + app web del docente (modelo A)."""
from __future__ import annotations

import argparse

from grafomotor.config import Config

AYUDA = "levanta la app web del docente en http://127.0.0.1:8000"


def agregar_argumentos(p: argparse.ArgumentParser) -> None:
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--puerto", type=int, default=8000)
    p.add_argument("--sin-recarga", action="store_true", help="desactiva la recarga automática")


def ejecutar(args: argparse.Namespace, cfg: Config) -> int:
    import uvicorn

    uvicorn.run("grafomotor.webapp.main:app", host=args.host, port=args.puerto,
                reload=not args.sin_recarga)
    return 0
