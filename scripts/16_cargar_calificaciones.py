"""Excel de calificación -> data/real/labels/etiquetas.csv (listo para entrenar y evaluar).

Lee `data/hojas_reales/calificacion_46_ninos.xlsx` (una fila por niño, columnas F01..F15 con 0/1,
edad en meses). Solo pasan los niños con las 15 figuras calificadas y la edad válida; los
incompletos se listan y se dejan fuera. Valida el resultado con el mismo lector que usan los
modelos (`cargar_etiquetas`).

  python scripts/16_cargar_calificaciones.py
  python scripts/16_cargar_calificaciones.py --excel otra.xlsx --salida otra.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from grafomotor.io import cargar_etiquetas  # noqa: E402

FIGURAS = [f"F{i:02d}" for i in range(1, 16)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--excel", default=str(RAIZ / "data/hojas_reales/calificacion_46_ninos.xlsx"))
    ap.add_argument("--salida", default=str(RAIZ / "data/real/labels/etiquetas.csv"))
    ap.add_argument("--hoja", default="Calificación")
    a = ap.parse_args()

    df = pd.read_excel(a.excel, sheet_name=a.hoja, header=0, skiprows=[1])   # fila 2 = descripciones
    df = df[df["child_id"].astype(str).str.startswith("NIN")].copy()

    filas, incompletos = [], {}
    for _, r in df.iterrows():
        faltan = [f for f in FIGURAS if pd.isna(r[f])]
        edad = r["edad_meses"]
        if faltan or pd.isna(edad):
            incompletos[r["child_id"]] = (["edad_meses"] if pd.isna(edad) else []) + faltan
            continue
        for f in FIGURAS:
            fila = {"child_id": r["child_id"], "edad_meses": int(edad), "figura_id": f,
                    "imagen_path": f"raw_reales/{r['child_id']}/{f}.jpg", "puntaje": int(r[f])}
            for col_xl, col in (("sexo", "sexo"), ("mano", "mano"), ("colegio", "colegio"),
                                ("evaluador", "evaluador"), ("fecha", "fecha")):
                if col_xl in df.columns and not pd.isna(r[col_xl]):
                    fila[col] = r[col_xl]
            filas.append(fila)

    print(f"niños completos: {len({f['child_id'] for f in filas})} de {len(df)}")
    if incompletos:
        for c, f in list(incompletos.items())[:10]:
            print(f"  incompleto {c}: faltan {len(f)} datos ({', '.join(f[:4])}…)")
        if len(incompletos) > 10:
            print(f"  … y {len(incompletos) - 10} niños incompletos más")
    if not filas:
        print("no hay niños completos todavía: no se escribió nada.")
        return 1

    salida = Path(a.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(filas).to_csv(salida, index=False)
    cargar_etiquetas(salida)                       # falla si el esquema o los rangos no valen
    tot = pd.DataFrame(filas)
    print(f"-> {salida}  ({len(tot)} filas, {tot['puntaje'].mean():.0%} figuras bien copiadas)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
