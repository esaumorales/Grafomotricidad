"""
Paso R3 (datos reales): Excel de calificación -> etiquetas.csv listo para entrenar y evaluar.

Lee el Excel (una fila por niño, columnas F01..F15 con 0/1 y la edad en meses). Solo pasan los
niños con las 15 figuras calificadas y la edad válida; los incompletos se listan y se dejan
fuera. El resultado se valida con el mismo lector que usan los modelos (`cargar_etiquetas`).
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from grafomotor.config import REPO_ROOT, Config
from grafomotor.io import cargar_etiquetas
from grafomotor.logs import obtener_logger

AYUDA = "datos reales: pasa el Excel de calificación (0/1 por figura) a etiquetas.csv"
log = obtener_logger(__name__)

FIGURAS = [f"F{i:02d}" for i in range(1, 16)]
COLUMNAS_OPCIONALES = ("sexo", "mano", "colegio", "evaluador", "fecha")


def agregar_argumentos(p: argparse.ArgumentParser) -> None:
    p.add_argument("--excel", default="data/hojas_reales/calificacion_46_ninos.xlsx",
                   help="Excel de calificación (relativo a la raíz del repo)")
    p.add_argument("--hoja", default="Calificación")
    p.add_argument("--salida", default=None, help="por defecto, rutas.labels de la configuración")


def _filas_del_nino(r: pd.Series, columnas: pd.Index) -> list[dict]:
    extra = {c: r[c] for c in COLUMNAS_OPCIONALES if c in columnas and not pd.isna(r[c])}
    return [{"child_id": r["child_id"], "edad_meses": int(r["edad_meses"]), "figura_id": f,
             "imagen_path": f"raw_reales/{r['child_id']}/{f}.jpg", "puntaje": int(r[f]), **extra}
            for f in FIGURAS]


def ejecutar(args: argparse.Namespace, cfg: Config) -> int:
    # la fila 2 del Excel trae las descripciones de cada columna: se salta
    df = pd.read_excel(REPO_ROOT / args.excel, sheet_name=args.hoja, header=0, skiprows=[1])
    df = df[df["child_id"].astype(str).str.startswith("NIN")]

    filas, incompletos = [], {}
    for _, r in df.iterrows():
        faltan = ([f for f in ("edad_meses",) if pd.isna(r[f])]
                  + [f for f in FIGURAS if pd.isna(r[f])])
        if faltan:
            incompletos[r["child_id"]] = faltan
        else:
            filas += _filas_del_nino(r, df.columns)

    completos = len({f["child_id"] for f in filas})
    log.info("niños completos: %d de %d", completos, len(df))
    for nino, faltan in list(incompletos.items())[:10]:
        log.warning("incompleto %s: faltan %d datos (%s…)", nino, len(faltan),
                    ", ".join(faltan[:4]))
    if len(incompletos) > 10:
        log.warning("… y %d niños incompletos más", len(incompletos) - 10)
    if not filas:
        log.error("no hay niños completos todavía: no se escribió nada")
        return 1

    salida = Path(args.salida) if args.salida else cfg.ruta("labels")
    salida.parent.mkdir(parents=True, exist_ok=True)
    tabla = pd.DataFrame(filas)
    tabla.to_csv(salida, index=False)
    cargar_etiquetas(salida)                       # falla si el esquema o los rangos no valen
    log.info("%d filas -> %s (%.0f%% de las figuras bien copiadas)", len(tabla), salida,
             100 * tabla["puntaje"].mean())
    return 0
