"""
Cadena completa de principio a fin.

  grafomotor todo --sinteticos        plantillas + datos falsos + modelo A
  grafomotor todo --sinteticos --dl   ... + modelo B y comparación A vs B
  grafomotor todo --dl                con los datos reales que haya en data/
"""
from __future__ import annotations

import argparse
import shutil

from grafomotor.config import REPO_ROOT, Config
from grafomotor.logs import obtener_logger

AYUDA = "ejecuta toda la cadena (modelo A y, con --dl, modelo B + comparación)"
log = obtener_logger(__name__)

PASOS_ML = ["validar", "preprocesar", "extraer-features", "entrenar-ml", "evaluar-ml"]
PASOS_DL = [("preparar-dl", []), ("entrenar-dl", ["--final"]), ("comparar", []),
            ("robustez", []), ("gradcam", []), ("practicidad", [])]


def agregar_argumentos(p: argparse.ArgumentParser) -> None:
    p.add_argument("--sinteticos", action="store_true", help="generar plantillas y datos falsos")
    p.add_argument("--n-ninos", type=int, default=150)
    p.add_argument("--dl", action="store_true", help="modelo B + comparación (requiere torch)")


def _asegurar_baremo() -> None:
    """Sin config/baremos.csv (no se versiona) se usa el de ejemplo, con aviso."""
    dir_cfg = REPO_ROOT / "config"
    if not (dir_cfg / "baremos.csv").exists():
        shutil.copy(dir_cfg / "baremos_ejemplo.csv", dir_cfg / "baremos.csv")
        log.warning("config/baremos.csv creado desde el EJEMPLO: sustitúyelo por la Tabla B.9")


def ejecutar(args: argparse.Namespace, cfg: Config) -> int:
    from grafomotor.cli import ejecutar_comando

    _asegurar_baremo()
    pasos: list[tuple[str, list[str]]] = []
    if args.sinteticos:
        pasos += [("plantillas", []), ("sinteticos", ["--n-ninos", str(args.n_ninos)])]
    pasos += [(p, []) for p in PASOS_ML]
    if args.dl:
        pasos += PASOS_DL

    for nombre, opciones in pasos:
        log.info("=" * 20 + f" {nombre} " + "=" * 20)
        codigo = ejecutar_comando(nombre, opciones, cfg)
        if codigo:
            log.error("el paso '%s' terminó con código %d; se detiene la cadena", nombre, codigo)
            return codigo
    log.info("cadena completa. Informe de ejemplo: grafomotor explicar --child-id NINO_0007")
    return 0
