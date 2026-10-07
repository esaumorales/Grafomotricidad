"""Hojas reales -> una imagen por figura (Etapa 0).

Lee los JPG de las hojas (`<niño>_p<N>.jpg`), localiza la cuadrícula, la orienta con las
plantillas y guarda la copia del niño de cada figura como `<salida>/<niño>/F01.jpg` ... `F15.jpg`.
Deja también una imagen de evidencia por hoja y `resumen_segmentacion.csv`.

  python scripts/14_segmentar_hojas.py
  python scripts/14_segmentar_hojas.py --solo NIN-05
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

import cv2
import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from grafomotor.preprocessing.hoja import normalizar_celda, segmentar_hoja  # noqa: E402


def _evidencia(h, ruta: Path) -> None:
    g = cv2.cvtColor(h.cuadricula, cv2.COLOR_GRAY2BGR)
    for y in h.lineas_y:
        cv2.line(g, (0, y), (g.shape[1], y), (0, 0, 255), 3)
    for x in h.lineas_x:
        cv2.line(g, (x, 0), (x, g.shape[0]), (0, 0, 255), 3)
    for i, t in enumerate(h.toca_borde):
        if t:
            cv2.putText(g, "SALE DE LA CELDA", (h.lineas_x[1] + 20, h.lineas_y[i] + 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 128, 255), 3)
    f = 1000 / max(g.shape)
    cv2.imwrite(str(ruta), cv2.resize(g, None, fx=f, fy=f, interpolation=cv2.INTER_AREA),
                [cv2.IMWRITE_JPEG_QUALITY, 85])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--origen", default="data/hojas_reales/jpg")
    ap.add_argument("--salida", default="data/raw_reales")
    ap.add_argument("--evidencia", default="data/hojas_reales/evidencia")
    ap.add_argument("--plantillas", default="data/templates")
    ap.add_argument("--solo", default=None, help="un niño, p. ej. NIN-05")
    a = ap.parse_args()
    origen, salida, evid = (RAIZ / a.origen, RAIZ / a.salida, RAIZ / a.evidencia)
    evid.mkdir(parents=True, exist_ok=True)
    plantillas = {p.stem: cv2.imread(str(p), 0) for p in sorted((RAIZ / a.plantillas).glob("F*.png"))}
    filas = []
    for f in sorted(origen.glob("*.jpg")):
        m = re.match(r"(.+)_p(\d)$", f.stem)
        if not m or (a.solo and m.group(1) != a.solo):
            continue
        nino, esperada = m.group(1), int(m.group(2))
        try:
            h = segmentar_hoja(cv2.imread(str(f), 0), plantillas, esperada)
        except ValueError as e:
            filas.append([nino, esperada, "", "", "", "", "", str(e)])
            print(f"{f.stem}: ERROR {e}")
            continue
        _evidencia(h, evid / f"{f.stem}.jpg")
        (salida / nino).mkdir(parents=True, exist_ok=True)
        for i, c in enumerate(h.copias):
            fid = f"F{(h.pagina - 1) * 5 + i + 1:02d}"
            cv2.imwrite(str(salida / nino / f"{fid}.jpg"), normalizar_celda(c),
                        [cv2.IMWRITE_JPEG_QUALITY, 95])
        filas.append([nino, esperada, h.pagina, round(h.puntaje_orientacion, 3),
                      round(h.margen_orientacion, 3), int(sum(h.toca_borde)),
                      "; ".join(h.avisos), ""])
        print(f"{f.stem}: pag {h.pagina} punt {h.puntaje_orientacion:.2f} "
              f"margen {h.margen_orientacion:.2f} sale {sum(h.toca_borde)} {h.avisos}")
    with open(evid / "resumen_segmentacion.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["nino", "pagina_archivo", "pagina_detectada", "puntaje", "margen",
                    "figuras_que_salen_de_la_celda", "avisos", "error"])
        w.writerows(filas)
    return 0


if __name__ == "__main__":
    sys.exit(main())
