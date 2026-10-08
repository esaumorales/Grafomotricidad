"""
Paso R2 (datos reales): deja listos los archivos finales de los modelos SIN necesitar
calificaciones.

Parte de `<raw>/<niño>/F01.jpg ... F15.jpg` (salida de `segmentar-hojas`) y escribe:

  labels/manifiesto.csv          una fila por niño y figura (edad_meses y puntaje en blanco)
  interim/                       modelo A: figura binaria registrada  <niño>__<figura>.png
  interim/_preprocesamiento.csv  calidad, registro y avisos por figura
  interim_dl/                    modelo B: recortes 224x224 en gris
  processed/features.parquet     modelo A: los 6 indicadores geométricos por figura

Usar siempre con `--config config/config_real.yaml` (rutas separadas de los datos sintéticos).
"""
from __future__ import annotations

import argparse
import time

import cv2
import pandas as pd

from grafomotor.artefactos import Artefactos
from grafomotor.config import Config
from grafomotor.dl.imagen import LADO, preparar_imagen
from grafomotor.features.extract import extraer_indicadores
from grafomotor.io import a_binaria, cargar_plantillas, leer_gris, ruta_foto
from grafomotor.logs import obtener_logger
from grafomotor.preprocessing import preprocesar_figura

AYUDA = "datos reales: manifiesto + interim + interim_dl + indicadores, sin calificaciones"
log = obtener_logger(__name__)


def agregar_argumentos(p: argparse.ArgumentParser) -> None:
    p.add_argument("--solo", default=None, help="un solo niño, p. ej. NIN-05")


def _manifiesto(cfg: Config, solo: str | None) -> pd.DataFrame:
    datos = cfg.ruta("raw").parent
    filas = [{"child_id": f.parent.name, "figura_id": f.stem,
              "imagen_path": f.relative_to(datos).as_posix(), "edad_meses": "", "puntaje": ""}
             for f in sorted(cfg.ruta("raw").glob("*/F??.jpg"))
             if not solo or f.parent.name == solo]
    return pd.DataFrame(filas)


def _combinar(nuevo: pd.DataFrame, ruta, solo: str | None) -> pd.DataFrame:
    """Con `--solo`, reemplaza únicamente las filas de ese niño y conserva las demás."""
    if not solo or not ruta.exists():
        return nuevo
    viejo = pd.read_parquet(ruta) if ruta.suffix == ".parquet" else pd.read_csv(ruta)
    resto = viejo[viejo["child_id"] != solo]
    return pd.concat([resto, nuevo], ignore_index=True).sort_values(
        ["child_id", "figura_id"], ignore_index=True)


def ejecutar(args: argparse.Namespace, cfg: Config) -> int:
    if cfg.ruta("raw").name == "raw":
        log.error("esta configuración apunta a los datos sintéticos (data/raw). "
                  "Usa:  grafomotor --config config/config_real.yaml preparar-reales")
        return 2
    art = Artefactos.de_config(cfg)
    plantillas = cargar_plantillas(cfg, estricto=True)
    pre_cfg = cfg.get("preprocesamiento", default={})
    lado = int(cfg.get("dl", "lado_px", default=LADO))

    man = _manifiesto(cfg, args.solo)
    ruta_man = cfg.ruta("labels").parent / "manifiesto.csv"
    ruta_man.parent.mkdir(parents=True, exist_ok=True)
    _combinar(man, ruta_man, args.solo).to_csv(ruta_man, index=False)
    log.info("manifiesto: %d figuras de %d niños -> %s", len(man), man["child_id"].nunique(),
             ruta_man)

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

    ra = _combinar(pd.DataFrame(rep_a), interim / "_preprocesamiento.csv", args.solo)
    rb = _combinar(pd.DataFrame(rep_b), art.preparacion_dl_de(lado), args.solo)
    fe = _combinar(pd.DataFrame(feats), art.features, args.solo)
    ra.to_csv(interim / "_preprocesamiento.csv", index=False)
    rb.to_csv(art.preparacion_dl_de(lado), index=False)
    art.features.parent.mkdir(parents=True, exist_ok=True)
    fe.to_parquet(art.features, index=False)

    avisos_a = ra.loc[ra["aviso"] != "", "aviso"].value_counts().to_dict()
    log.info("modelo A: %d binarias -> %s · registro OK %d · avisos %s", len(ra), interim,
             int(ra["registro_ok"].sum()), avisos_a)
    log.info("modelo B: %d recortes %dx%d -> %s · avisos %s", len(rb), lado, lado, carpeta_dl,
             rb.loc[rb["aviso"] != "", "aviso"].value_counts().to_dict())
    log.info("indicadores: %d figuras -> %s", len(fe), art.features)
    return 0
