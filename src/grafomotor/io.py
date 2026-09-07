"""Carga y validación del dataset de etiquetas."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

COLUMNAS_REQUERIDAS = [
    "child_id", "edad_meses", "figura_id", "imagen_path", "puntaje",
]
COLUMNAS_OPCIONALES = ["sexo", "evaluador", "fecha", "version_baremo"]


class ErrorEtiquetas(ValueError):
    pass


def cargar_etiquetas(path: str | Path) -> pd.DataFrame:
    """Lee el CSV de etiquetas y valida el esquema (ver docs/DATOS.md)."""
    df = pd.read_csv(path)
    faltan = [c for c in COLUMNAS_REQUERIDAS if c not in df.columns]
    if faltan:
        raise ErrorEtiquetas(f"Faltan columnas obligatorias: {faltan}")

    if not df["puntaje"].isin([0, 1]).all():
        malos = sorted(set(df["puntaje"]) - {0, 1})
        raise ErrorEtiquetas(f"'puntaje' debe ser 0 o 1; valores extraños: {malos}")

    if not df["edad_meses"].between(36, 71).all():
        fuera = df.loc[~df["edad_meses"].between(36, 71), "child_id"].unique().tolist()
        raise ErrorEtiquetas(
            f"edad_meses fuera del rango 3;0–5;11 (36–71) en: {fuera}. "
            "El baremo del CUMANIN-2 llega a 6;11 pero el estudio se limita a 3–5."
        )

    dup = df.duplicated(subset=["child_id", "figura_id"]).sum()
    if dup:
        raise ErrorEtiquetas(f"{dup} filas duplicadas por (child_id, figura_id).")

    return df


def resumen_dataset(df: pd.DataFrame) -> dict:
    """Estadísticas para detectar desbalance / efecto suelo antes de entrenar."""
    por_nino = df.groupby("child_id")
    pd_por_nino = por_nino["puntaje"].sum()
    return {
        "n_ninos": df["child_id"].nunique(),
        "n_imagenes": len(df),
        "figuras": sorted(df["figura_id"].unique().tolist()),
        "imagenes_por_nino_media": round(por_nino.size().mean(), 1),
        "tasa_acierto_global": round(df["puntaje"].mean(), 3),
        "tasa_acierto_por_figura": por_figura_acierto(df),
        "PD_min_max": (int(pd_por_nino.min()), int(pd_por_nino.max())),
        "ninos_PD_0": int((pd_por_nino == 0).sum()),  # posible efecto suelo (3 años)
        "tramos_edad": tramos_presentes(df),
    }


def por_figura_acierto(df: pd.DataFrame) -> dict:
    return {
        fig: round(sub["puntaje"].mean(), 2)
        for fig, sub in df.groupby("figura_id")
    }


def tramos_presentes(df: pd.DataFrame) -> dict:
    from grafomotor.scoring.baremo import tramo_de_edad

    tr = df.assign(tramo=df["edad_meses"].map(tramo_de_edad))
    return tr.groupby("tramo")["child_id"].nunique().to_dict()
