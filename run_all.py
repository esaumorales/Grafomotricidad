"""
Ejecuta toda la cadena de principio a fin.

  python run_all.py --sinteticos     genera plantillas + datos falsos y corre todo
  python run_all.py                   usa lo que ya haya en data/ (tus datos reales)

Pasos: gen_plantillas -> [99_generar_datos_sinteticos] -> 00 validar -> 01 preprocesar
       -> 02 features -> 03 entrenar -> 04 evaluar
"""
from __future__ import annotations

import argparse
import runpy
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).parent


def _run(mod: str, args: list[str] | None = None) -> None:
    print(f"\n{'=' * 70}\n>> {mod} {' '.join(args or [])}\n{'=' * 70}")
    sys.argv = [mod, *(args or [])]
    try:
        runpy.run_path(str(RAIZ / mod), run_name="__main__")
    except SystemExit as e:
        if e.code not in (0, None):
            raise RuntimeError(f"{mod} terminó con código {e.code}") from None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sinteticos", action="store_true", help="generar plantillas y datos falsos")
    ap.add_argument("--n-ninos", type=int, default=150)
    a = ap.parse_args()

    # baremo: si no hay baremos.csv, usa el de ejemplo
    cfg_dir = RAIZ / "config"
    if not (cfg_dir / "baremos.csv").exists():
        shutil.copy(cfg_dir / "baremos_ejemplo.csv", cfg_dir / "baremos.csv")
        print("[info] config/baremos.csv creado desde el ejemplo (SUSTITUIR por el oficial).")

    if a.sinteticos:
        _run("scripts/gen_plantillas.py")
        _run("scripts/99_generar_datos_sinteticos.py", ["--n-ninos", str(a.n_ninos)])

    for paso in ["00_validar_datos.py", "01_preprocesar.py", "02_extraer_features.py",
                 "03_entrenar.py", "04_evaluar.py"]:
        _run(f"scripts/{paso}")

    print("\n\n*** CADENA COMPLETA ***")
    print("Demo del informe:  python scripts/05_explicar_demo.py --child-id NINO_0007")
    print("App web:           python scripts/06_servir_web.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
