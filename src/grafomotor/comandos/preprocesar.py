"""Paso 01 (modelo A): fotos de data/raw/ -> figuras binarias registradas en data/interim/."""
from __future__ import annotations

import argparse

import cv2
import pandas as pd

from grafomotor.config import Config
from grafomotor.io import cargar_etiquetas, cargar_plantillas, ruta_foto
from grafomotor.logs import obtener_logger
from grafomotor.preprocessing import preprocesar_figura

AYUDA = "modelo A: preprocesa las fotos (binarizado + registro a plantilla) -> data/interim/"
log = obtener_logger(__name__)


def agregar_argumentos(p: argparse.ArgumentParser) -> None:
    pass


def ejecutar(args: argparse.Namespace, cfg: Config) -> int:
    etiquetas = cargar_etiquetas(cfg.ruta("labels"))
    plantillas = cargar_plantillas(cfg, estricto=False)
    salida = cfg.ruta("interim")
    salida.mkdir(parents=True, exist_ok=True)
    pre_cfg = cfg.get("preprocesamiento", default={})

    filas = []
    for fila in etiquetas.itertuples(index=False):
        base = {"child_id": fila.child_id, "figura_id": fila.figura_id}
        foto = ruta_foto(cfg, fila.imagen_path)
        if fila.figura_id not in plantillas:
            filas.append({**base, "estado": "sin_plantilla"})
            continue
        if not foto.exists():
            filas.append({**base, "estado": "sin_foto"})
            continue
        res = preprocesar_figura(str(foto), plantillas[fila.figura_id], pre_cfg)
        destino = salida / f"{fila.child_id}__{fila.figura_id}.png"
        cv2.imwrite(str(destino), res.figura_bin)
        filas.append({**base, "estado": "ok", "interim_path": destino.name,
                      "calidad": res.calidad, "registro_ok": res.registro_ok,
                      "rotacion_deg": round(res.rotacion_deg, 1), "aviso": res.aviso or ""})

    rep = pd.DataFrame(filas)
    rep.to_csv(salida / "_preprocesamiento.csv", index=False)
    ok = rep[rep["estado"] == "ok"]
    log.info("%d/%d figuras procesadas · registro OK %d · calidad media %.2f",
             len(ok), len(rep), int(ok["registro_ok"].sum()) if len(ok) else 0,
             ok["calidad"].mean() if len(ok) else float("nan"))
    if (rep["estado"] != "ok").any():
        log.warning("sin procesar: %s", rep.loc[rep["estado"] != "ok", "estado"]
                    .value_counts().to_dict())
    if len(ok) and (ok["aviso"] != "").any():
        log.warning("avisos: %s", ok.loc[ok["aviso"] != "", "aviso"].value_counts().to_dict())
    return 0
