"""
Paso R1 (datos reales): de la foto de la hoja a una imagen por figura.

Lee los JPG de las hojas (`<niño>_p<N>.jpg`), localiza la cuadrícula, la orienta y guarda la
copia del niño de cada figura como `<salida>/<niño>/F01.jpg ... F15.jpg`. Deja también una
imagen de evidencia por hoja y `resumen_segmentacion.csv` (con los avisos de cada hoja).
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

import cv2

from grafomotor.config import REPO_ROOT, Config
from grafomotor.logs import obtener_logger
from grafomotor.preprocessing.hoja import HojaSegmentada, normalizar_celda, segmentar_hoja

AYUDA = "datos reales: recorta cada hoja (5 figuras) en una imagen por figura -> data/raw_reales/"
log = obtener_logger(__name__)


def agregar_argumentos(p: argparse.ArgumentParser) -> None:
    p.add_argument("--origen", default="data/hojas_reales/jpg",
                   help="carpeta con <niño>_p<N>.jpg (relativa a la raíz del repo)")
    p.add_argument("--salida", default="data/raw_reales", help="carpeta de las figuras recortadas")
    p.add_argument("--evidencia", default="data/hojas_reales/evidencia",
                   help="imágenes de evidencia y resumen_segmentacion.csv")
    p.add_argument("--solo", default=None, help="un solo niño, p. ej. NIN-05")


def _evidencia(h: HojaSegmentada, ruta: Path) -> None:
    """Hoja rectificada con las líneas detectadas en rojo y las figuras que se salen marcadas."""
    g = cv2.cvtColor(h.cuadricula, cv2.COLOR_GRAY2BGR)
    for y in h.lineas_y:
        cv2.line(g, (0, y), (g.shape[1], y), (0, 0, 255), 3)
    for x in h.lineas_x:
        cv2.line(g, (x, 0), (x, g.shape[0]), (0, 0, 255), 3)
    for i, sale in enumerate(h.toca_borde):
        if sale:
            pos = (h.lineas_x[1] + 20, h.lineas_y[i] + 60)
            cv2.putText(g, "SALE DE LA CELDA", pos, cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 128, 255), 3)
    f = 1000 / max(g.shape)
    cv2.imwrite(str(ruta), cv2.resize(g, None, fx=f, fy=f, interpolation=cv2.INTER_AREA),
                [cv2.IMWRITE_JPEG_QUALITY, 85])


def ejecutar(args: argparse.Namespace, cfg: Config) -> int:
    origen, salida, evid = (REPO_ROOT / args.origen, REPO_ROOT / args.salida,
                            REPO_ROOT / args.evidencia)
    evid.mkdir(parents=True, exist_ok=True)
    rutas_plantillas = sorted(cfg.ruta("templates").glob("F*.png"))
    plantillas = {p.stem: cv2.imread(str(p), 0) for p in rutas_plantillas}

    filas = []
    for foto in sorted(origen.glob("*.jpg")):
        m = re.match(r"(.+)_p(\d)$", foto.stem)
        if not m or (args.solo and m.group(1) != args.solo):
            continue
        nino, esperada = m.group(1), int(m.group(2))
        try:
            h = segmentar_hoja(cv2.imread(str(foto), 0), plantillas, esperada)
        except ValueError as e:
            filas.append([nino, esperada, "", "", "", "", "", str(e)])
            log.warning("%s: %s", foto.stem, e)
            continue
        _evidencia(h, evid / f"{foto.stem}.jpg")
        (salida / nino).mkdir(parents=True, exist_ok=True)
        for i, celda in enumerate(h.copias):
            fid = f"F{(h.pagina - 1) * 5 + i + 1:02d}"
            cv2.imwrite(str(salida / nino / f"{fid}.jpg"), normalizar_celda(celda),
                        [cv2.IMWRITE_JPEG_QUALITY, 95])
        filas.append([nino, esperada, h.pagina, round(h.puntaje_orientacion, 3),
                      round(h.margen_orientacion, 3), int(sum(h.toca_borde)),
                      "; ".join(h.avisos), ""])
        if h.avisos:
            log.warning("%s: %s", foto.stem, "; ".join(h.avisos))

    with open(evid / "resumen_segmentacion.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["nino", "pagina_archivo", "pagina_detectada", "puntaje", "margen",
                    "figuras_que_salen_de_la_celda", "avisos", "error"])
        w.writerows(filas)
    con_aviso = sum(1 for f in filas if f[6] or f[7])
    log.info("%d hojas segmentadas · %d con aviso -> %s", len(filas), con_aviso, salida)
    return 0
