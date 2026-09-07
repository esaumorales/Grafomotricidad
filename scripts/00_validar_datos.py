"""Valida el CSV de etiquetas y las carpetas. Imprime un resumen del dataset."""
from __future__ import annotations

import json
import sys

from grafomotor.config import load_config
from grafomotor.io import cargar_etiquetas, resumen_dataset


def main() -> int:
    cfg = load_config()
    path = cfg.ruta("labels")
    if not path.exists():
        print(f"[ERROR] No existe {path}. Copia data/labels/etiquetas_ejemplo.csv -> etiquetas.csv")
        return 1
    df = cargar_etiquetas(path)
    print(json.dumps(resumen_dataset(df), indent=2, ensure_ascii=False))

    # avisos útiles antes de entrenar
    r = resumen_dataset(df)
    if r["ninos_PD_0"] > 0:
        print(f"\n[AVISO] {r['ninos_PD_0']} niño(s) con PD=0 (posible efecto suelo a los 3 años).")
    flojas = [k for k, v in r["tasa_acierto_por_figura"].items() if v < 0.1 or v > 0.9]
    if flojas:
        print(f"[AVISO] Figuras muy desbalanceadas (tasa <0.1 o >0.9): {flojas}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
