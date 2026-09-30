"""Paso 07 (modelo B): preprocesamiento mínimo -> recortes 224×224 en data/interim_dl/."""
from __future__ import annotations

import argparse
import time

import cv2
import pandas as pd

from grafomotor.artefactos import Artefactos
from grafomotor.config import Config
from grafomotor.dl.imagen import LADO, preparar_imagen
from grafomotor.io import cargar_etiquetas, ruta_foto
from grafomotor.logs import obtener_logger

AYUDA = "modelo B: perspectiva + recorte 224×224 de cada foto -> data/interim_dl/"
log = obtener_logger(__name__)


def agregar_argumentos(p: argparse.ArgumentParser) -> None:
    pass


def ejecutar(args: argparse.Namespace, cfg: Config) -> int:
    art = Artefactos.de_config(cfg)
    art.interim_dl.mkdir(parents=True, exist_ok=True)
    lado = int(cfg.get("dl", "lado_px", default=LADO))

    filas = []
    for fila in cargar_etiquetas(cfg.ruta("labels")).itertuples(index=False):
        base = {"child_id": fila.child_id, "figura_id": fila.figura_id}
        t0 = time.perf_counter()
        try:
            img, aviso = preparar_imagen(str(ruta_foto(cfg, fila.imagen_path)), lado)
        except FileNotFoundError:
            filas.append({**base, "dl_path": None, "aviso": "sin_foto", "seg": 0.0})
            continue
        nombre = f"{fila.child_id}__{fila.figura_id}.png"
        cv2.imwrite(str(art.interim_dl / nombre), img)
        filas.append({**base, "dl_path": nombre, "aviso": aviso or "",
                      "seg": round(time.perf_counter() - t0, 4)})

    rep = pd.DataFrame(filas)
    rep.to_csv(art.preparacion_dl, index=False)
    log.info("%d/%d recortes -> %s · %.1f ms por figura", rep["dl_path"].notna().sum(),
             len(rep), art.interim_dl, rep["seg"].mean() * 1000)
    avisos = rep.loc[rep["aviso"] != "", "aviso"].value_counts().to_dict()
    if avisos:
        log.warning("avisos: %s", avisos)
    return 0
