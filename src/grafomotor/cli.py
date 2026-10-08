"""
Punto de entrada único:  `grafomotor <comando> [opciones]`  (o `python -m grafomotor`).

Cada comando vive en `grafomotor/comandos/<modulo>.py` y expone:
    AYUDA: str
    agregar_argumentos(parser) -> None
    ejecutar(args, cfg) -> int

Los módulos se importan SOLO al usarse, así `grafomotor validar` no carga PyTorch.
Los scripts numerados de scripts/ son envoltorios de estos mismos comandos.
"""
from __future__ import annotations

import argparse
import importlib
import logging
import sys
from collections.abc import Sequence

from grafomotor.config import Config, load_config
from grafomotor.logs import configurar_logs

# nombre del comando -> (módulo, paso de la cadena)
COMANDOS: dict[str, tuple[str, str]] = {
    "plantillas": ("plantillas", "-"),
    "sinteticos": ("sinteticos", "99"),
    "validar": ("validar", "00"),
    "preprocesar": ("preprocesar", "01"),
    "extraer-features": ("extraer_features", "02"),
    "entrenar-ml": ("entrenar_ml", "03"),
    "evaluar-ml": ("evaluar_ml", "04"),
    "explicar": ("explicar", "05"),
    "servir": ("servir", "06"),
    "preparar-dl": ("preparar_dl", "07"),
    "entrenar-dl": ("entrenar_dl", "08"),
    "comparar": ("comparar", "09"),
    "robustez": ("robustez", "10"),
    "gradcam": ("gradcam", "11"),
    "practicidad": ("practicidad", "12"),
    "resumen-variantes": ("resumen_variantes", "13"),
    "ensamblar-dl": ("ensamblar_dl", "14"),
    "errores": ("errores", "15"),
    "acuerdo-evaluadores": ("acuerdo_evaluadores", "16"),
    "identificar": ("identificar", "17"),
    "curva-aprendizaje": ("curva_aprendizaje", "18"),
    "segmentar-hojas": ("segmentar_hojas", "R1"),
    "preparar-reales": ("preparar_reales", "R2"),
    "cargar-calificaciones": ("cargar_calificaciones", "R3"),
    "todo": ("todo", "-"),
}


def _modulo(nombre: str):
    return importlib.import_module(f"grafomotor.comandos.{COMANDOS[nombre][0]}")


def ejecutar_comando(nombre: str, argv: Sequence[str] | None = None,
                     config: str | Config | None = None) -> int:
    """Ejecuta un comando por nombre (lo usan los scripts numerados y `todo`).

    `config` puede ser una ruta a config.yaml o una Config ya cargada.
    """
    mod = _modulo(nombre)
    p = argparse.ArgumentParser(prog=f"grafomotor {nombre}", description=mod.AYUDA)
    mod.agregar_argumentos(p)
    args = p.parse_args(list(argv) if argv is not None else [])
    configurar_logs()
    cfg = config if isinstance(config, Config) else load_config(config)
    return int(mod.ejecutar(args, cfg) or 0)


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    ayuda = "\n".join(f"  {paso:>3}  {n}" for n, (_, paso) in COMANDOS.items())
    p = argparse.ArgumentParser(
        prog="grafomotor",
        description="Evaluación grafomotora: modelo A (XGBoost) vs modelo B (red profunda).",
        epilog=f"comandos (paso · nombre):\n{ayuda}\n\n"
               "Ayuda de un comando:  grafomotor <comando> --help",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--config", default=None, help="ruta a config.yaml (por defecto config/)")
    p.add_argument("-v", "--verbose", action="store_true", help="logs de depuración")
    p.add_argument("comando", choices=list(COMANDOS), metavar="comando")
    p.add_argument("opciones", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    a = p.parse_args(argv)
    configurar_logs(logging.DEBUG if a.verbose else logging.INFO)
    return ejecutar_comando(a.comando, a.opciones, a.config)


if __name__ == "__main__":
    sys.exit(main())
