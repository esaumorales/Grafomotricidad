"""
Paso 00: valida etiquetas.csv y responde "¿alcanzan los datos?" antes de entrenar.

- Resumen general (niños, figuras, efecto suelo, edades, colegios).
- BALANCE POR FIGURA: cada figura aprende con los niños que la copiaron; lo que limita es
  la clase MINORITARIA (p. ej. pocos errores en la línea recta). Se avisa según los mínimos
  orientativos de config.yaml > datos (A necesita menos que B).
- Reparto por edad (3, 4, 5 años) y, si existe la columna `colegio`, por colegio.
"""
from __future__ import annotations

import argparse
import json

import pandas as pd

from grafomotor.config import Config
from grafomotor.io import cargar_etiquetas, guardar_json, resumen_dataset
from grafomotor.logs import obtener_logger

AYUDA = "valida etiquetas.csv y revisa si alcanzan los datos (balance por figura, edades)"
log = obtener_logger(__name__)


def agregar_argumentos(p: argparse.ArgumentParser) -> None:
    pass


def balance_por_figura(df: pd.DataFrame, min_ml: int, min_dl: int) -> pd.DataFrame:
    """Correctas, incorrectas y clase minoritaria por figura, con un veredicto por modelo."""
    t = df.groupby("figura_id")["puntaje"].agg(correctas="sum", n="size")
    t["incorrectas"] = t["n"] - t["correctas"]
    t["minoritaria"] = t[["correctas", "incorrectas"]].min(axis=1)
    t["tasa_acierto"] = (t["correctas"] / t["n"]).round(2)
    t["alcanza_A"] = t["minoritaria"] >= min_ml
    t["alcanza_B"] = t["minoritaria"] >= min_dl
    return t.reset_index()


def reparto(df: pd.DataFrame, columna: str) -> dict:
    return df.drop_duplicates("child_id")[columna].value_counts().sort_index().to_dict()


def ejecutar(args: argparse.Namespace, cfg: Config) -> int:
    ruta = cfg.ruta("labels")
    if not ruta.exists():
        log.error("no existe %s: copia data/labels/etiquetas_ejemplo.csv -> etiquetas.csv", ruta)
        return 1
    df = cargar_etiquetas(ruta)
    resumen = resumen_dataset(df)
    min_ml = int(cfg.get("datos", "min_minoritaria_ml", default=30))
    min_dl = int(cfg.get("datos", "min_minoritaria_dl", default=100))

    balance = balance_por_figura(df, min_ml, min_dl)
    edades = reparto(df.assign(anios=df["edad_meses"] // 12), "anios")
    resumen["ninos_por_edad"] = {f"{k}_anios": int(v) for k, v in edades.items()}
    if "colegio" in df.columns:
        resumen["ninos_por_colegio"] = reparto(df, "colegio")
    resumen["balance_por_figura"] = balance.to_dict(orient="records")
    guardar_json(resumen, cfg.ruta("processed") / "validacion_datos.json")

    print(json.dumps({k: v for k, v in resumen.items() if k != "balance_por_figura"},
                     indent=2, ensure_ascii=False))
    print("\nBalance por figura (clase minoritaria = la respuesta menos común):")
    print(balance[["figura_id", "correctas", "incorrectas", "minoritaria", "alcanza_A",
                   "alcanza_B"]].to_string(index=False))

    if resumen["ninos_PD_0"]:
        log.warning("%d niño(s) con PD=0 (posible efecto suelo a los 3 años)",
                    resumen["ninos_PD_0"])
    for modelo, col, minimo in (("A", "alcanza_A", min_ml), ("B", "alcanza_B", min_dl)):
        cortas = balance.loc[~balance[col], "figura_id"].tolist()
        if cortas:
            log.warning("modelo %s: %d figura(s) con menos de %d ejemplos de la clase "
                        "minoritaria (reportarlas con cautela): %s", modelo, len(cortas),
                        minimo, cortas)
    if edades and min(edades.values()) < 0.5 * max(edades.values()):
        log.warning("reparto por edad desigual %s: el modelo rendirá peor en la edad con "
                    "menos niños", resumen["ninos_por_edad"])
    return 0
