"""Datos reales -> archivos finales para los modelos, SIN necesitar las calificaciones.

Parte de `data/raw_reales/<niño>/F01.jpg ... F15.jpg` (salida de 14_segmentar_hojas.py) y deja,
bajo data/real/ (separado de los datos sintéticos):

  labels/manifiesto.csv      una fila por niño y figura (edad_meses y puntaje en blanco)
  interim/                   modelo A: figura binaria registrada  <niño>__<figura>.png
  interim/_preprocesamiento.csv   calidad, registro y avisos por figura
  interim_dl/                recortes 224x224 en gris para el modelo B
  processed/features.parquet los 6 indicadores geométricos por figura (modelo A)

  python scripts/15_preparar_reales.py
  python scripts/15_preparar_reales.py --solo NIN-05
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from grafomotor.artefactos import Artefactos  # noqa: E402
from grafomotor.config import load_config  # noqa: E402
from grafomotor.dl.imagen import LADO, preparar_imagen  # noqa: E402
from grafomotor.features.extract import extraer_indicadores  # noqa: E402
from grafomotor.io import a_binaria, cargar_plantillas, leer_gris, ruta_foto  # noqa: E402
from grafomotor.logs import configurar_logs, obtener_logger  # noqa: E402
from grafomotor.preprocessing import preprocesar_figura  # noqa: E402

log = obtener_logger("preparar_reales")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", default=str(RAIZ / "config" / "config_real.yaml"))
    ap.add_argument("--solo", default=None, help="un niño, p. ej. NIN-05")
    a = ap.parse_args()
    configurar_logs()
    cfg = load_config(a.config)
    art = Artefactos.de_config(cfg)
    plantillas = cargar_plantillas(cfg, estricto=True)
    pre_cfg = cfg.get("preprocesamiento", default={})
    lado = int(cfg.get("dl", "lado_px", default=LADO))
    datos = cfg.ruta("raw").parent

    # 1. manifiesto (sin calificaciones)
    filas = []
    for foto in sorted(cfg.ruta("raw").glob("*/F??.jpg")):
        if a.solo and foto.parent.name != a.solo:
            continue
        filas.append({"child_id": foto.parent.name, "figura_id": foto.stem,
                      "imagen_path": foto.relative_to(datos).as_posix(),
                      "edad_meses": "", "puntaje": ""})
    man = pd.DataFrame(filas)
    ruta_man = cfg.ruta("labels").parent / "manifiesto.csv"
    ruta_man.parent.mkdir(parents=True, exist_ok=True)
    man.to_csv(ruta_man, index=False)
    log.info("manifiesto: %d figuras de %d niños -> %s", len(man), man["child_id"].nunique(),
             ruta_man)

    # 2. modelo A (binaria registrada) + 3. modelo B (recorte 224) + 4. indicadores
    interim, carpeta_dl = cfg.ruta("interim"), art.carpeta_dl(lado)
    interim.mkdir(parents=True, exist_ok=True)
    carpeta_dl.mkdir(parents=True, exist_ok=True)
    rep_a, rep_b, feats = [], [], []
    for fila in man.itertuples(index=False):
        base = {"child_id": fila.child_id, "figura_id": fila.figura_id}
        foto = ruta_foto(cfg, fila.imagen_path)
        nombre = f"{fila.child_id}__{fila.figura_id}.png"

        res = preprocesar_figura(str(foto), plantillas[fila.figura_id], pre_cfg)
        cv2.imwrite(str(interim / nombre), res.figura_bin)
        rep_a.append({**base, "interim_path": nombre, "calidad": res.calidad,
                      "registro_ok": res.registro_ok, "rotacion_deg": round(res.rotacion_deg, 1),
                      "aviso": res.aviso or ""})

        t0 = time.perf_counter()
        img, aviso = preparar_imagen(str(foto), lado)
        cv2.imwrite(str(carpeta_dl / nombre), img)
        rep_b.append({**base, "dl_path": nombre, "aviso": aviso or "",
                      "seg": round(time.perf_counter() - t0, 4)})

        vec = extraer_indicadores(a_binaria(leer_gris(interim / nombre)),
                                  plantillas[fila.figura_id], fila.figura_id,
                                  cfg.figuras.get(fila.figura_id, {}))
        feats.append({**base, **vec.valores, **{f"raw_{k}": v for k, v in vec.raw.items()}})

    pd.DataFrame(rep_a).to_csv(interim / "_preprocesamiento.csv", index=False)
    pd.DataFrame(rep_b).to_csv(art.preparacion_dl_de(lado), index=False)
    art.features.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(feats).to_parquet(art.features, index=False)

    ra, rb = pd.DataFrame(rep_a), pd.DataFrame(rep_b)
    log.info("modelo A: %d binarias -> %s · registro OK %d · avisos %s", len(ra), interim,
             int(ra["registro_ok"].sum()), ra.loc[ra["aviso"] != "", "aviso"].value_counts().to_dict())
    log.info("modelo B: %d recortes %dx%d -> %s · avisos %s", len(rb), lado, lado, carpeta_dl,
             rb.loc[rb["aviso"] != "", "aviso"].value_counts().to_dict())
    log.info("indicadores: %d figuras -> %s", len(feats), art.features)
    return 0


if __name__ == "__main__":
    sys.exit(main())
