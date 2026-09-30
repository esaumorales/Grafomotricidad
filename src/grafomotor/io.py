"""
Entrada/salida del proyecto: etiquetas, imágenes, plantillas y JSON.

Las funciones de imagen importan OpenCV de forma perezosa para que los módulos que
solo necesitan las etiquetas (p. ej. la API web al arrancar) no carguen OpenCV.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from grafomotor.config import Config

EDAD_MIN_MESES = 36   # 3;0
EDAD_MAX_MESES = 71   # 5;11
UMBRAL_PLANTILLA = 127

COLUMNAS_REQUERIDAS = [
    "child_id", "edad_meses", "figura_id", "imagen_path", "puntaje",
]
# hoja de registro: fecha_nacimiento, sexo, hora_inicio, hora_termino, mano (derecha/izquierda)
COLUMNAS_OPCIONALES = ["sexo", "evaluador", "fecha", "version_baremo",
                       "fecha_nacimiento", "hora_inicio", "hora_termino", "mano",
                       "colegio"]   # colegio: para la validación externa por colegio


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

    en_rango = df["edad_meses"].between(EDAD_MIN_MESES, EDAD_MAX_MESES)
    if not en_rango.all():
        fuera = df.loc[~en_rango, "child_id"].unique().tolist()
        raise ErrorEtiquetas(
            f"edad_meses fuera del rango 3;0–5;11 (36–71) en: {fuera}. "
            "El baremo del CUMANIN (Tabla B.9) llega más allá, pero el estudio se limita a 3–5."
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


# --------------------------------------------------------------------------- #
# Imágenes y plantillas
# --------------------------------------------------------------------------- #
def leer_gris(ruta: str | Path) -> np.ndarray:
    """Lee una imagen en escala de grises; error claro si no existe o no se puede leer."""
    import cv2

    img = cv2.imread(str(ruta), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"no se pudo leer la imagen: {ruta}")
    return img


def a_binaria(gris: np.ndarray) -> np.ndarray:
    """Imagen en gris (plantilla o figura de data/interim) -> binaria 0/255 (trazo = 255)."""
    return (gris > UMBRAL_PLANTILLA).astype(np.uint8) * 255


def ruta_plantilla(cfg: Config, figura_id: str) -> Path:
    return cfg.ruta("templates") / f"{figura_id}.png"


def cargar_plantilla(cfg: Config, figura_id: str) -> np.ndarray:
    return a_binaria(leer_gris(ruta_plantilla(cfg, figura_id)))


def cargar_plantillas(cfg: Config, estricto: bool = True) -> dict[str, np.ndarray]:
    """Plantillas binarias de todas las figuras de config.yaml.

    estricto=True: falla si falta alguna. estricto=False: omite las que falten (app web).
    """
    out = {}
    for fid in cfg.figuras:
        if ruta_plantilla(cfg, fid).exists():
            out[fid] = cargar_plantilla(cfg, fid)
        elif estricto:
            raise FileNotFoundError(
                f"falta la plantilla {ruta_plantilla(cfg, fid)}. "
                "Genérala con: python scripts/gen_plantillas.py")
    return out


def ruta_foto(cfg: Config, imagen_path: str) -> Path:
    """`imagen_path` de etiquetas.csv es relativo a data/ (p. ej. raw/NINO_0007/F03.jpg)."""
    return cfg.ruta("raw").parent / imagen_path


# --------------------------------------------------------------------------- #
# JSON
# --------------------------------------------------------------------------- #
def guardar_json(datos: Any, ruta: str | Path) -> Path:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, indent=2, ensure_ascii=False, default=_a_json),
                    encoding="utf-8")
    return ruta


def leer_json(ruta: str | Path) -> Any:
    return json.loads(Path(ruta).read_text(encoding="utf-8"))


def _a_json(x: Any) -> Any:
    """Tipos de numpy/pandas/Path que json no serializa por sí solo."""
    if isinstance(x, np.integer):
        return int(x)
    if isinstance(x, np.floating):
        return float(x)
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, Path):
        return str(x)
    raise TypeError(f"no serializable a JSON: {type(x).__name__}")
