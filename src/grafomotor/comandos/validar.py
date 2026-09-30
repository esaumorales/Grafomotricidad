"""Paso 00: valida etiquetas.csv y resume el dataset (desbalance, efecto suelo, edades)."""
from __future__ import annotations

import argparse
import json

from grafomotor.config import Config
from grafomotor.io import cargar_etiquetas, resumen_dataset
from grafomotor.logs import obtener_logger

AYUDA = "valida data/labels/etiquetas.csv y resume el dataset"
log = obtener_logger(__name__)

TASA_EXTREMA = 0.1   # figuras con tasa de acierto < 0.1 o > 0.9 se avisan


def agregar_argumentos(p: argparse.ArgumentParser) -> None:
    pass


def ejecutar(args: argparse.Namespace, cfg: Config) -> int:
    ruta = cfg.ruta("labels")
    if not ruta.exists():
        log.error("no existe %s: copia data/labels/etiquetas_ejemplo.csv -> etiquetas.csv", ruta)
        return 1
    resumen = resumen_dataset(cargar_etiquetas(ruta))
    print(json.dumps(resumen, indent=2, ensure_ascii=False))

    if resumen["ninos_PD_0"]:
        log.warning("%d niño(s) con PD=0 (posible efecto suelo a los 3 años)",
                    resumen["ninos_PD_0"])
    extremas = [f for f, v in resumen["tasa_acierto_por_figura"].items()
                if v < TASA_EXTREMA or v > 1 - TASA_EXTREMA]
    if extremas:
        log.warning("figuras muy desbalanceadas (tasa <%.1f o >%.1f): %s",
                    TASA_EXTREMA, 1 - TASA_EXTREMA, extremas)
    return 0
