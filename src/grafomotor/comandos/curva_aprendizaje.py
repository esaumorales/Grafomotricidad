"""
Paso 18: CURVA DE APRENDIZAJE. ¿Alcanzan los datos o ayudarían más niños?

Para cada fold de prueba (siempre el mismo, completo) se entrena con una fracción de los
niños de entrenamiento (20 %, 40 %, ... 100 %) y se mide kappa por figura y CCI de la PD.
Si la curva sigue subiendo al 100 %, más niños mejorarían el modelo; si se aplana, conviene
invertir en calidad de fotos y etiquetas.

  grafomotor curva-aprendizaje                         modelo A (rápido)
  grafomotor curva-aprendizaje --arq resnet18          modelo B (entrena 5 × 5 redes)
  grafomotor curva-aprendizaje --arq resnet18 --rapido pocas épocas, solo para probar

Modelo A: hiperparámetros fijos (los del modelo final) para aislar el efecto de la
cantidad de datos. Salidas: curva_aprendizaje_<modelo>.json y .md
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from grafomotor.artefactos import Artefactos
from grafomotor.config import Config
from grafomotor.evaluation.particiones import folds_de, particiones_de_config
from grafomotor.evaluation.reporte import evaluar_oof, resumen_corto
from grafomotor.io import cargar_etiquetas, guardar_json
from grafomotor.logs import obtener_logger
from grafomotor.scoring.baremo import cargar_baremo

AYUDA = "curva de aprendizaje: rendimiento según cuántos niños se usan para entrenar"
log = obtener_logger(__name__)

FRACCIONES = (0.2, 0.4, 0.6, 0.8, 1.0)
SEMILLA = 20260930


def agregar_argumentos(p: argparse.ArgumentParser) -> None:
    p.add_argument("--arq", default=None, help="variante de B; sin esto, el modelo A")
    p.add_argument("--rapido", action="store_true", help="modelo B: 2+2 épocas (solo prueba)")


def submuestra_ninos(ninos: np.ndarray, fraccion: float, semilla: int) -> set:
    rng = np.random.default_rng(semilla)
    n = max(2, round(fraccion * len(ninos)))
    return set(rng.choice(ninos, size=min(n, len(ninos)), replace=False))


def _predictor_ml(cfg: Config, art: Artefactos, etiquetas: pd.DataFrame):
    """Devuelve (tabla con X, función entrenar-y-predecir) para el modelo A."""
    from xgboost import XGBClassifier

    from grafomotor import ORDEN
    from grafomotor.model.registry import cargar_modelo
    from grafomotor.model.train import pesos_balanceados

    datos = etiquetas.merge(pd.read_parquet(art.features), on=["child_id", "figura_id"])
    params = cargar_modelo(art.dir_modelo_ml)[0].get_params()
    balanceado = cfg.get("modelo", "class_weight") == "balanced"

    def entrenar_predecir(tr: pd.DataFrame, te: pd.DataFrame) -> np.ndarray:
        m = XGBClassifier(**params)
        y = tr["puntaje"].to_numpy()
        m.fit(tr[ORDEN].to_numpy(float), y,
              sample_weight=pesos_balanceados(y) if balanceado else None)
        return m.predict_proba(te[ORDEN].to_numpy(float))[:, 1]

    return datos, entrenar_predecir


def _predictor_dl(cfg: Config, art: Artefactos, etiquetas: pd.DataFrame, variante: str,
                  rapido: bool):
    from grafomotor.dl.entrenar import CONFIG_POR_DEFECTO, entrenar_fold, predecir
    from grafomotor.io import leer_json

    cfg_dl = {**CONFIG_POR_DEFECTO, **dict(cfg.get("dl", default={}))}
    if art.historial_dl(variante).exists():          # misma configuración que la variante
        cfg_dl.update(leer_json(art.historial_dl(variante)).get("cfg", {}))
    if rapido:
        cfg_dl.update(epocas_fase1=2, epocas_fase2=2)
    carpeta = art.carpeta_dl(int(cfg_dl.get("lado_px", 224)))
    prep = pd.read_csv(carpeta / "_preparacion_dl.csv")[["child_id", "figura_id", "dl_path"]]
    datos = etiquetas.merge(prep, on=["child_id", "figura_id"]).dropna(subset=["dl_path"])
    figuras = list(cfg.figuras)

    def entrenar_predecir(tr: pd.DataFrame, te: pd.DataFrame) -> np.ndarray:
        res = entrenar_fold(tr, carpeta, figuras, cfg_dl, verbose=False)
        return predecir(res.modelo, te, carpeta, figuras)

    return datos, entrenar_predecir


def ejecutar(args: argparse.Namespace, cfg: Config) -> int:
    art = Artefactos.de_config(cfg)
    nombre = args.arq or "ml"
    etiquetas = cargar_etiquetas(cfg.ruta("labels"))
    particiones = particiones_de_config(cfg, etiquetas)
    if args.arq:
        datos, entrenar_predecir = _predictor_dl(cfg, art, etiquetas, args.arq, args.rapido)
    else:
        datos, entrenar_predecir = _predictor_ml(cfg, art, etiquetas)
    datos = datos.assign(fold=folds_de(datos["child_id"], particiones))
    baremo = cargar_baremo(cfg.ruta("baremos"))
    n_clases = int(cfg.get("scoring", "n_clases", default=2))

    resultados = []
    for frac in FRACCIONES:
        partes, n_train = [], []
        for k in sorted(datos["fold"].unique()):
            prueba = datos[datos["fold"] == k]
            resto = datos[datos["fold"] != k]
            elegidos = submuestra_ninos(resto["child_id"].unique(), frac, SEMILLA + int(k))
            entreno = resto[resto["child_id"].isin(elegidos)]
            n_train.append(len(elegidos))
            prob = entrenar_predecir(entreno, prueba)
            partes.append(prueba[["child_id", "figura_id", "edad_meses", "fold"]].assign(
                y=prueba["puntaje"].to_numpy(), prob=prob, yhat=(prob >= 0.5).astype(float)))
        corto = resumen_corto(evaluar_oof(pd.concat(partes), baremo, n_clases))
        fila = {"fraccion": frac, "ninos_entrenamiento_media": round(float(np.mean(n_train)), 1),
                "kappa_figura": corto["kappa_figura"], "cci_PD": corto["cci_PD"],
                "exactitud_balanceada": corto["exactitud_balanceada"]}
        resultados.append(fila)
        log.info("%3.0f %% (%.0f niños): κ %.3f · CCI %.3f", 100 * frac,
                 fila["ninos_entrenamiento_media"], fila["kappa_figura"], fila["cci_PD"])

    ultimo, penultimo = resultados[-1], resultados[-2]
    sube = ultimo["kappa_figura"] - penultimo["kappa_figura"]
    conclusion = ("la curva todavía sube: más niños probablemente mejorarían el modelo"
                  if sube > 0.01 else
                  "la curva se aplana: más niños ayudarían poco; priorizar calidad de datos")
    salida = {"modelo": nombre, "curva": resultados,
              "mejora_ultimo_tramo_kappa": round(float(sube), 3), "conclusion": conclusion}
    guardar_json(salida, art.curva_aprendizaje(nombre))
    md = ["| % niños | niños (media) | κ por figura | CCI de la PD | exactitud balanceada |",
          "|---|---|---|---|---|"]
    md += [f"| {int(100 * r['fraccion'])} % | {r['ninos_entrenamiento_media']} | "
           f"{r['kappa_figura']} | {r['cci_PD']} | {r['exactitud_balanceada']} |"
           for r in resultados]
    md += ["", f"**Conclusión:** {conclusion} (último tramo: {sube:+.3f} de κ)."]
    art.curva_aprendizaje(nombre, "md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))
    return 0
