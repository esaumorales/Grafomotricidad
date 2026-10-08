"""
Paso 05: muestra el informe para el docente de un niño.

  grafomotor explicar --child-id NINO_0007      pipeline real (modelo + fotos)
  grafomotor explicar --simular --nivel derivar  caso SIMULADO, para ver el texto sin datos
"""
from __future__ import annotations

import argparse

import numpy as np

from grafomotor.config import Config
from grafomotor.logs import obtener_logger

AYUDA = "muestra el informe en lenguaje natural para el docente (real o simulado)"
log = obtener_logger(__name__)

ACCIONES = ("ninguna", "reforzar_y_revaluar", "derivar")
PERCENTIL_SIMULADO = {"ninguna": 60, "reforzar_y_revaluar": 10, "derivar": 1}


def agregar_argumentos(p: argparse.ArgumentParser) -> None:
    p.add_argument("--child-id")
    p.add_argument("--nombre", default="el niño / la niña")
    p.add_argument("--simular", action="store_true")
    p.add_argument("--nivel", choices=ACCIONES, default="reforzar_y_revaluar")


def _informe_simulado(accion: str, nombre: str) -> None:
    from grafomotor.explain import construir_informe, explicar_para_docente
    from grafomotor.model.predict import PrediccionFigura, agregar_sesion
    from grafomotor.scoring.niveles import nivel_desde_percentil

    rng = np.random.default_rng(7)
    figuras = {"F01": "línea recta", "F03": "cruz", "F04": "círculo",
               "F05": "cuadrado", "F06": "triángulo", "F10": "rombo"}
    base = 0.85 if accion == "ninguna" else 0.45
    # indicadores más bajos en cierre y ángulos para los casos con dificultades
    desvio = {"precision_modelo": 0, "vertices": .1, "error_angular": -.15,
              "cierre": -.25, "intersecciones": 0, "proporcion": -.05}
    preds = []
    for fid in figuras:
        ind = {k: float(np.clip(base + d + rng.normal(0, .08), 0, 1)) for k, d in desvio.items()}
        prob = float(np.clip(np.mean(list(ind.values())), .05, .95))
        preds.append(PrediccionFigura(fid, int(prob >= .5), round(prob, 3), ind))

    # SHAP simulado coherente: cierre y ángulos con contribución negativa
    agg = {"precision_modelo": .01, "vertices": .04, "error_angular": -.06,
           "cierre": -.11, "intersecciones": .02, "proporcion": -.03}
    shap = {"agg_signed": agg, "agg_abs": {k: abs(v) for k, v in agg.items()},
            "por_figura": [agg] * len(preds), "base_value": 0.0}
    exp = explicar_para_docente(
        agregar_sesion("DEMO", 40, preds),
        nivel_desde_percentil(PERCENTIL_SIMULADO[accion], n_clases=2),
        shap, figuras,
        {"umbral_relevancia_shap": .03, "max_fortalezas": 2, "max_dificultades": 3,
         "umbral_confianza_baja": .6},
        nombre_nino=nombre)
    inf = construir_informe(exp)
    print(inf.informe_docente_md)
    print("\n--- PANEL TÉCNICO (especialista) ---")
    print(inf.panel_tecnico["resumen"])
    if inf.alertas_estilo:
        log.warning("jerga detectada en el texto del docente: %s", inf.alertas_estilo)


def ejecutar(args: argparse.Namespace, cfg: Config) -> int:
    if args.simular or not args.child_id:
        _informe_simulado(args.nivel, args.nombre)
        return 0

    from grafomotor.io import cargar_etiquetas, ruta_foto
    from grafomotor.webapp.service import Servicio

    etiquetas = cargar_etiquetas(cfg.ruta("labels"))
    sub = etiquetas[etiquetas["child_id"] == args.child_id]
    if sub.empty:
        log.error("child_id %s no está en las etiquetas", args.child_id)
        return 1
    fotos = {f: ruta_foto(cfg, p)
             for f, p in zip(sub["figura_id"], sub["imagen_path"], strict=True)}
    res = Servicio().evaluar_sesion(args.child_id, int(sub["edad_meses"].iloc[0]), fotos,
                                    args.nombre)
    print(res["informe_docente_md"])
    print("\n--- PANEL TÉCNICO ---")
    print(res["panel_tecnico"]["resumen"])
    return 0
