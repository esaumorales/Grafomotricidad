"""
Dataset SINTÉTICO para ejecutar la cadena completa sin datos reales.

    data/raw/<child_id>/<figura_id>.jpg   "fotos" (plantilla perturbada sobre papel)
    data/labels/etiquetas.csv             edad, figura, puntaje 0/1, evaluador...

Todo esto es de MENTIRA: sirve para probar el código, no dice nada del rendimiento
real. Para pasar a datos reales ver ESTADO.md.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
import pandas as pd

from grafomotor.augment.label_safe import deformacion_elastica
from grafomotor.config import Config
from grafomotor.io import EDAD_MAX_MESES, EDAD_MIN_MESES, cargar_plantillas
from grafomotor.logs import obtener_logger

log = obtener_logger(__name__)

UMBRAL_SEVERIDAD_CORRECTA = 0.45   # severidad < umbral -> el "evaluador" pone 1


@dataclass(frozen=True)
class ParametrosSinteticos:
    n_ninos: int = 150
    semilla: int = 7
    fraccion_doble: float = 0.2     # niños con un 2.º evaluador simulado (0 = ninguno)
    ruido_evaluador: float = 0.06   # desacuerdo del 2.º evaluador cerca del umbral


def perturbar(plantilla: np.ndarray, severidad: float, rng: np.random.Generator) -> np.ndarray:
    """severidad 0 (perfecta) .. 1 (muy mal): temblor, rotación, proporción y huecos."""
    im = deformacion_elastica(plantilla.copy(), alpha=4 + 20 * severidad, sigma=6)
    ang = float(rng.normal(0, 18 * severidad))                       # rotación
    M = cv2.getRotationMatrix2D((im.shape[1] / 2, im.shape[0] / 2), ang, 1.0)
    im = cv2.warpAffine(im, M, im.shape[::-1], flags=cv2.INTER_NEAREST)
    fx = 1 + float(rng.normal(0, 0.25 * severidad))                  # proporción
    im = cv2.resize(im, None, fx=max(0.5, fx), fy=1.0, interpolation=cv2.INTER_NEAREST)
    im = cv2.resize(im, plantilla.shape[::-1], interpolation=cv2.INTER_NEAREST)
    if rng.random() < severidad:                                     # fallo de cierre
        ys, xs = np.where(im > 0)
        if len(xs):
            k = rng.integers(len(xs))
            cv2.circle(im, (int(xs[k]), int(ys[k])), int(8 + 20 * severidad), 0, -1)
    return im


def a_foto(figura_bin: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Figura binaria -> 'foto' de hoja: papel claro, trazo oscuro, ruido, leve giro."""
    alto, ancho, lado = 900, 700, 520
    hoja = np.full((alto, ancho), 235, np.uint8)
    hoja += rng.integers(-6, 6, (alto, ancho), dtype=np.int16).clip(0, 255).astype(np.uint8)
    fig = cv2.resize(figura_bin, (lado, lado), interpolation=cv2.INTER_NEAREST)
    y0, x0 = (alto - lado) // 2, (ancho - lado) // 2
    zona = hoja[y0:y0 + lado, x0:x0 + lado]
    zona[fig > 0] = rng.integers(20, 60)
    M = cv2.getRotationMatrix2D((ancho / 2, alto / 2), float(rng.normal(0, 2.5)), 1.0)
    return cv2.warpAffine(hoja, M, (ancho, alto), borderValue=235)


def generar_dataset(cfg: Config, params: ParametrosSinteticos | None = None) -> pd.DataFrame:
    """Escribe las fotos y etiquetas.csv; devuelve las etiquetas."""
    params = params or ParametrosSinteticos()
    plantillas = cargar_plantillas(cfg)
    raw = cfg.ruta("raw")
    raw.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(params.semilla)
    figuras = list(cfg.figuras)

    filas, dobles = [], []
    # generador aparte: el dataset principal no cambia al activar la doble calificación
    rng_doble = np.random.default_rng(params.semilla + 1)
    ninos_dobles = set(rng_doble.choice(np.arange(1, params.n_ninos + 1),
                                        int(params.fraccion_doble * params.n_ninos),
                                        replace=False))
    for i in range(1, params.n_ninos + 1):
        cid = f"NINO_{i:04d}"
        edad = int(rng.integers(EDAD_MIN_MESES, EDAD_MAX_MESES + 1))
        # "habilidad": sesgada a población normal, peor cuanto más pequeño
        habilidad = float(np.clip(rng.beta(5, 2) - (60 - edad) / 120, 0.05, 0.98))
        (raw / cid).mkdir(parents=True, exist_ok=True)
        for j, fid in enumerate(figuras):
            dificultad = j / max(1, len(figuras) - 1) * 0.5          # figuras finales más difíciles
            severidad = float(np.clip(1 - habilidad + dificultad + rng.normal(0, 0.08), 0, 1))
            rel = f"raw/{cid}/{fid}.jpg"
            foto = a_foto(perturbar(plantillas[fid], severidad, rng), rng)
            cv2.imwrite(str(raw.parent / rel), foto, [cv2.IMWRITE_JPEG_QUALITY, 88])
            filas.append({
                "child_id": cid, "edad_meses": edad, "sexo": rng.choice(["F", "M"]),
                "figura_id": fid, "imagen_path": rel,
                "puntaje": int(severidad < UMBRAL_SEVERIDAD_CORRECTA),
                "evaluador": rng.choice(["EXP_A", "EXP_B"]),
                "fecha": "2026-03-01", "version_baremo": "SINTETICO",
            })
            if i in ninos_dobles:   # 2.º evaluador: discrepa sobre todo en casos límite
                sev_2 = severidad + rng_doble.normal(0, params.ruido_evaluador)
                dobles.append({"child_id": cid, "figura_id": fid,
                               "puntaje": int(sev_2 < UMBRAL_SEVERIDAD_CORRECTA)})

    df = pd.DataFrame(filas)
    destino = cfg.ruta("labels")
    destino.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(destino, index=False)
    if dobles:
        pd.DataFrame(dobles).to_csv(cfg.ruta("doble_calificacion"), index=False)
        log.info("doble calificación simulada: %d niños -> %s", len(ninos_dobles),
                 cfg.ruta("doble_calificacion"))
    log.info("%d niños · %d imágenes -> %s", params.n_ninos, len(df), raw)
    log.info("tasa de acierto global %.3f · niños con PD=0: %d", df["puntaje"].mean(),
             int((df.groupby("child_id")["puntaje"].sum() == 0).sum()))
    log.warning("datos SINTÉTICOS: sustitúyelos por los reales (ver ESTADO.md)")
    return df
