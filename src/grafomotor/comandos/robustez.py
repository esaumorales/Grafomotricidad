"""
Paso 10: robustez de A y B ante fotos peores que las de entrenamiento.

1. Degradaciones sintéticas (sombra, desenfoque, inclinación, brillo; 3 niveles)
   aplicadas a la FOTO original de cada niño; cada modelo usa el de su fold.
2. Doble foto real, si existe data/labels/fotos_aula.csv (child_id, figura_id, imagen_path).

Las probabilidades de A se guardan en una caché (A es lo lento y no depende de B):
la primera corrida tarda ~25 min con 30 niños; las siguientes solo corren B.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Callable

import numpy as np
import pandas as pd

from grafomotor.artefactos import Artefactos
from grafomotor.config import Config
from grafomotor.evaluation.degradaciones import DEGRADACIONES, NIVELES, degradar
from grafomotor.evaluation.degradaciones import VERSION as VERSION_DEGRADACIONES
from grafomotor.evaluation.metrics import icc_acuerdo_absoluto, metricas_binarias
from grafomotor.evaluation.particiones import folds_de, obtener_particiones
from grafomotor.io import cargar_etiquetas, guardar_json, leer_gris, ruta_foto
from grafomotor.logs import obtener_logger
from grafomotor.predictores import PredictorA, PredictorB, modelos_ml_por_fold

AYUDA = "robustez de A y B: degradaciones sintéticas y doble foto de aula"
log = obtener_logger(__name__)

Transformacion = Callable[[np.ndarray, int], np.ndarray]
SEMILLA_MUESTRA = 20260930


def agregar_argumentos(p: argparse.ArgumentParser) -> None:
    p.add_argument("--arq", default=None, help="variante de B (p. ej. resnet18_robusto)")
    p.add_argument("--muestra-ninos", type=int, default=None,
                   help="niños evaluados (0 = todos); por defecto config.yaml")


class CacheA:
    """Probabilidades de A por (condición, niño, figura), invalidadas si cambia A.

    La firma cubre particiones, modelo A, indicadores y configuración de preprocesamiento;
    además cada fila guarda la versión de las degradaciones con que se calculó.
    """

    def __init__(self, cfg: Config):
        art = Artefactos.de_config(cfg)
        self.ruta = art.cache_robustez_ml
        h = hashlib.md5()
        for f in (art.particiones, art.dir_modelo_ml / "manifiesto.json", art.features):
            h.update(f.read_bytes() if f.exists() else b"")
        for seccion in ("preprocesamiento", "modelo"):
            h.update(json.dumps(cfg.get(seccion, default={}), sort_keys=True).encode())
        self.firma = h.hexdigest()
        self.datos: dict[tuple[str, str, str], float] = {}
        if self.ruta.exists():
            df = pd.read_parquet(self.ruta)
            version = df.get("version_degradaciones", 1)   # cachés antiguas: versión 1
            df = df[(df["firma"] == self.firma) & (version == VERSION_DEGRADACIONES)]
            claves = zip(df["condicion"], df["child_id"], df["figura_id"], strict=True)
            self.datos = dict(zip(claves, df["p_A"], strict=True))
        log.info("caché de A: %d predicciones reutilizables", len(self.datos))

    def guardar(self) -> None:
        pd.DataFrame([{"firma": self.firma, "version_degradaciones": VERSION_DEGRADACIONES,
                       "condicion": c, "child_id": n, "figura_id": f, "p_A": p}
                      for (c, n, f), p in self.datos.items()]
                     ).to_parquet(self.ruta, index=False)


def resumen(df: pd.DataFrame) -> dict:
    """κ, exactitud balanceada, CCI de la PD y fallos para A y B en una condición."""
    out = {}
    for m in ("A", "B"):
        p = df[f"p_{m}"]
        medidas = df[p.notna()]
        r = metricas_binarias(medidas["y"], (medidas[f"p_{m}"] >= 0.5).astype(int))
        pd_nino = df.assign(h=(p >= 0.5).astype(int)).groupby("child_id")[["y", "h"]].sum()
        out[m] = {"kappa": r["kappa"], "exactitud_balanceada": r["exactitud_balanceada"],
                  "cci_PD": icc_acuerdo_absoluto(pd_nino["y"], pd_nino["h"]),
                  "tasa_fallos": round(float(p.isna().mean()), 4)}
    return out


class EvaluadorRobustez:
    def __init__(self, cfg: Config, variante: str, etiquetas: pd.DataFrame,
                 particiones: pd.DataFrame):
        self.cfg, self.etiquetas, self.particiones = cfg, etiquetas, particiones
        self.b = PredictorB.desde_variante(cfg, variante, "folds")
        self.cache = CacheA(cfg)
        self._a: PredictorA | None = None

    @property
    def a(self) -> PredictorA:
        """A se construye solo si falta algo en la caché (reentrena un XGBoost por fold)."""
        if self._a is None:
            modelos, _, _ = modelos_ml_por_fold(self.cfg, self.etiquetas, self.particiones)
            self._a = PredictorA(self.cfg, modelos)
        return self._a

    def condicion(self, filas: pd.DataFrame, nombre: str, transformar: Transformacion) -> dict:
        partes = []
        for k, g in filas.groupby("fold"):
            grises = [transformar(leer_gris(r), i) for i, r in zip(g.index, g["ruta"], strict=True)]
            p_b = self.b.predecir_lote(grises, list(g["figura_id"]), int(k))
            p_a = []
            for gris, nino, fig in zip(grises, g["child_id"], g["figura_id"], strict=True):
                clave = (nombre, nino, fig)
                if clave not in self.cache.datos:
                    self.cache.datos[clave] = self.a.predecir(gris, fig, int(k))
                p_a.append(self.cache.datos[clave])
            partes.append(g.assign(p_A=p_a, p_B=p_b))
        r = resumen(pd.concat(partes))
        log.info("%-22s κ A %.3f · κ B %.3f · CCI A %.3f · CCI B %.3f", nombre,
                 r["A"]["kappa"], r["B"]["kappa"], r["A"]["cci_PD"], r["B"]["cci_PD"])
        return r


def tabla_markdown(salida: dict) -> str:
    filas = {"sin degradar": salida["sin_degradar"], **salida["degradaciones"]}
    if isinstance(salida["doble_foto_aula"], dict):
        filas["doble foto (aula)"] = salida["doble_foto_aula"]
    lin = ["| Condición | κ A | κ B | CCI PD A | CCI PD B | fallos A | fallos B |",
           "|---|---|---|---|---|---|---|"]
    lin += [f"| {n} | {r['A']['kappa']} | {r['B']['kappa']} | {r['A']['cci_PD']} | "
            f"{r['B']['cci_PD']} | {r['A']['tasa_fallos']} | {r['B']['tasa_fallos']} |"
            for n, r in filas.items()]
    return "\n".join(lin)


def _filas(cfg: Config, df: pd.DataFrame, particiones: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["fold"] = folds_de(df["child_id"], particiones)
    df["y"] = df["puntaje"]
    df["ruta"] = [ruta_foto(cfg, p) for p in df["imagen_path"]]
    return df


def ejecutar(args: argparse.Namespace, cfg: Config) -> int:
    art = Artefactos.de_config(cfg)
    variante = args.arq or cfg.get("dl", "arquitectura", default="resnet18")
    cfg_r = cfg.get("comparacion", "robustez", default={})
    n_muestra = (args.muestra_ninos if args.muestra_ninos is not None
                 else int(cfg_r.get("muestra_ninos", 40)))

    etiquetas = cargar_etiquetas(cfg.ruta("labels"))
    particiones = obtener_particiones(art.particiones, etiquetas,
                                      int(cfg.get("comparacion", "folds", default=5)))
    ninos = sorted(etiquetas["child_id"].unique())
    if n_muestra and n_muestra < len(ninos):
        ninos = sorted(np.random.default_rng(SEMILLA_MUESTRA).choice(ninos, n_muestra,
                                                                      replace=False))
    base = _filas(cfg, etiquetas[etiquetas["child_id"].isin(ninos)], particiones)
    log.info("robustez · %d niños · %d figuras · B = %s", len(ninos), len(base), variante)

    ev = EvaluadorRobustez(cfg, variante, etiquetas, particiones)
    salida = {"variante": variante, "n_ninos": len(ninos),
              "sin_degradar": ev.condicion(base, "sin_degradar", lambda g, i: g),
              "degradaciones": {}}
    for tipo in cfg_r.get("degradaciones", list(DEGRADACIONES)):
        for nivel in cfg_r.get("niveles", list(NIVELES)):
            nombre = f"{tipo}/{nivel}"
            salida["degradaciones"][nombre] = ev.condicion(
                base, nombre, lambda g, i, t=tipo, n=nivel: degradar(g, t, n, int(i)))

    aula = cfg.ruta("fotos_aula")
    if aula.exists():
        fa = pd.read_csv(aula).merge(etiquetas[["child_id", "figura_id", "puntaje"]],
                                     on=["child_id", "figura_id"], how="inner")
        salida["doble_foto_aula"] = ev.condicion(_filas(cfg, fa, particiones), "aula",
                                                 lambda g, i: g)
    else:
        salida["doble_foto_aula"] = ("sin datos: falta data/labels/fotos_aula.csv; la robustez "
                                     "solo se estimó con degradaciones sintéticas")
        log.warning("sin doble foto de aula: solo degradaciones sintéticas")

    ev.cache.guardar()
    guardar_json(salida, art.robustez(variante))
    md = tabla_markdown(salida)
    art.robustez(variante, "md").write_text(md, encoding="utf-8")
    print(md)
    return 0
