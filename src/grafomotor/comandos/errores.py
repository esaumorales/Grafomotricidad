"""
Paso 15: galería de ERRORES de un modelo, para revisarlos a mano.

Con pocos datos, mirar cada figura mal calificada es la forma más rápida de encontrar
fotos malas o etiquetas dudosas (buena práctica en imagen médica con datos pequeños).
Los errores se ordenan por CONFIANZA: un error con probabilidad 0.97 suele ser una
etiqueta a revisar; uno con 0.52 es un caso límite.

  grafomotor errores                         modelo A
  grafomotor errores --arq resnet18          una variante de B

Salidas en data/processed/errores_<modelo>/:
  errores.csv                       todos los errores, del más al menos confiado
  <figura>_falsos_positivos.png     el modelo dijo "correcta" y el experto 0
  <figura>_falsos_negativos.png     el modelo dijo "incorrecta" y el experto 1
"""
from __future__ import annotations

import argparse

import cv2
import numpy as np
import pandas as pd

from grafomotor.artefactos import Artefactos
from grafomotor.config import Config
from grafomotor.io import cargar_etiquetas, leer_gris, ruta_foto
from grafomotor.logs import obtener_logger

AYUDA = "galería de errores de un modelo (A o una variante de B) para revisarlos a mano"
log = obtener_logger(__name__)

LADO_MINIATURA = 200
COLUMNAS_MOSAICO = 6


def agregar_argumentos(p: argparse.ArgumentParser) -> None:
    p.add_argument("--arq", default=None, help="variante de B; sin esto, el modelo A")
    p.add_argument("--max-por-figura", type=int, default=18,
                   help="miniaturas por figura y tipo de error")


def tabla_errores(oof: pd.DataFrame) -> pd.DataFrame:
    """Errores medidos, con su tipo y confianza (|prob − 0.5| · 2, de 0 a 1)."""
    err = oof[oof["yhat"].notna() & (oof["yhat"] != oof["y"])].copy()
    err["tipo"] = np.where(err["yhat"] == 1, "falso_positivo", "falso_negativo")
    err["confianza"] = ((err["prob"] - 0.5).abs() * 2).round(3)
    return err.sort_values("confianza", ascending=False).reset_index(drop=True)


def miniatura(gris: np.ndarray, texto: str) -> np.ndarray:
    """Foto reducida a un cuadrado con un rótulo abajo."""
    h, w = gris.shape
    esc = LADO_MINIATURA / max(h, w)
    img = cv2.resize(gris, (max(1, int(w * esc)), max(1, int(h * esc))),
                     interpolation=cv2.INTER_AREA)
    lienzo = np.full((LADO_MINIATURA + 22, LADO_MINIATURA), 255, np.uint8)
    y0, x0 = (LADO_MINIATURA - img.shape[0]) // 2, (LADO_MINIATURA - img.shape[1]) // 2
    lienzo[y0:y0 + img.shape[0], x0:x0 + img.shape[1]] = img
    cv2.putText(lienzo, texto, (4, LADO_MINIATURA + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42, 0, 1,
                cv2.LINE_AA)
    return cv2.cvtColor(lienzo, cv2.COLOR_GRAY2BGR)


def mosaico(miniaturas: list[np.ndarray]) -> np.ndarray:
    filas = []
    for i in range(0, len(miniaturas), COLUMNAS_MOSAICO):
        fila = miniaturas[i:i + COLUMNAS_MOSAICO]
        fila += [np.full_like(miniaturas[0], 255)] * (COLUMNAS_MOSAICO - len(fila))
        filas.append(np.hstack(fila))
    return np.vstack(filas)


def ejecutar(args: argparse.Namespace, cfg: Config) -> int:
    art = Artefactos.de_config(cfg)
    nombre = args.arq or "ml"
    oof = pd.read_parquet(art.oof_dl(args.arq) if args.arq else art.oof_ml)
    etiquetas = cargar_etiquetas(cfg.ruta("labels"))[["child_id", "figura_id", "imagen_path"]]
    err = tabla_errores(oof).merge(etiquetas, on=["child_id", "figura_id"], how="left")

    carpeta = art.dir_errores(nombre)
    carpeta.mkdir(parents=True, exist_ok=True)
    err.to_csv(carpeta / "errores.csv", index=False)

    for (fig, tipo), g in err.groupby(["figura_id", "tipo"]):
        minis = [miniatura(leer_gris(ruta_foto(cfg, r.imagen_path)),
                           f"{r.child_id} p={r.prob:.2f}")
                 for r in g.head(args.max_por_figura).itertuples(index=False)]
        plural = {"falso_positivo": "falsos_positivos", "falso_negativo": "falsos_negativos"}
        cv2.imwrite(str(carpeta / f"{fig}_{plural[tipo]}.png"), mosaico(minis))

    resumen = err.groupby(["figura_id", "tipo"]).size().unstack(fill_value=0)
    print(resumen.to_string())
    confiados = int((err["confianza"] >= 0.8).sum())
    log.info("%d errores (%d con confianza >= 0.8: revisar primero, pueden ser etiquetas "
             "dudosas) -> %s", len(err), confiados, carpeta)
    return 0
