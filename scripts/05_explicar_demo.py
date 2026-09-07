"""
Demo del informe para docente sobre un caso.

Si hay modelo + fotos: usa el pipeline real.
Si no, usa un caso SIMULADO para poder ver el texto sin datos:
    python scripts/05_explicar_demo.py --simular --nivel derivar
"""
from __future__ import annotations

import argparse
import sys

import numpy as np


def _demo_simulada(accion: str, nombre: str) -> None:
    from grafomotor.explain import construir_informe, explicar_para_docente
    from grafomotor.model.predict import PrediccionFigura, agregar_sesion
    from grafomotor.scoring.niveles import nivel_desde_T

    rng = np.random.default_rng(7)
    figuras = {"F01": "círculo", "F02": "cruz", "F03": "cuadrado",
               "F04": "triángulo", "F05": "cruz oblicua", "F06": "rombo"}
    T = {"ninguna": 52, "reforzar_y_revaluar": 37, "derivar": 27}[accion]

    # indicadores más bajos en cierre/ángulos para el caso con dificultades
    preds = []
    for fid in figuras:
        base = 0.85 if accion == "ninguna" else 0.45
        ind = {
            "precision_modelo": float(np.clip(base + rng.normal(0, .08), 0, 1)),
            "vertices": float(np.clip(base + .1 + rng.normal(0, .08), 0, 1)),
            "error_angular": float(np.clip(base - .15 + rng.normal(0, .08), 0, 1)),
            "cierre": float(np.clip(base - .25 + rng.normal(0, .08), 0, 1)),
            "intersecciones": float(np.clip(base + rng.normal(0, .08), 0, 1)),
            "proporcion": float(np.clip(base - .05 + rng.normal(0, .08), 0, 1)),
        }
        prob = float(np.clip(np.mean(list(ind.values())), .05, .95))
        preds.append(PrediccionFigura(fid, int(prob >= .5), round(prob, 3), ind))

    sesion = agregar_sesion("DEMO", 40, preds)
    nivel = nivel_desde_T(T, n_clases=2)

    # SHAP simulado coherente: cierre y ángulos con contribución negativa
    agg = {"precision_modelo": .01, "vertices": .04, "error_angular": -.06,
           "cierre": -.11, "intersecciones": .02, "proporcion": -.03}
    shap = {"agg_signed": agg, "agg_abs": {k: abs(v) for k, v in agg.items()},
            "por_figura": [agg] * len(preds), "base_value": 0.0}

    exp = explicar_para_docente(sesion, nivel, shap, figuras,
                                {"umbral_relevancia_shap": .03, "max_fortalezas": 2,
                                 "max_dificultades": 3, "umbral_confianza_baja": .6},
                                nombre_nino=nombre)
    inf = construir_informe(exp)
    print(inf.informe_docente_md)
    print("\n--- PANEL TÉCNICO (especialista) ---")
    print(inf.panel_tecnico["resumen"])
    if inf.alertas_estilo:
        print("\n[!!] jerga detectada en el texto del docente:", inf.alertas_estilo)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--child-id")
    ap.add_argument("--nombre", default="el niño / la niña")
    ap.add_argument("--simular", action="store_true")
    ap.add_argument("--nivel", choices=["ninguna", "reforzar_y_revaluar", "derivar"],
                    default="reforzar_y_revaluar")
    a = ap.parse_args()

    if a.simular or not a.child_id:
        _demo_simulada(a.nivel, a.nombre)
        return 0

    # camino real
    from grafomotor.io import cargar_etiquetas
    from grafomotor.config import load_config
    from grafomotor.webapp.service import Servicio

    cfg = load_config()
    df = cargar_etiquetas(cfg.ruta("labels"))
    sub = df[df["child_id"] == a.child_id]
    if sub.empty:
        print(f"[ERROR] child_id {a.child_id} no está en las etiquetas.")
        return 1
    fotos = {r["figura_id"]: cfg.ruta("raw") / r["imagen_path"].replace("raw/", "")
             for _, r in sub.iterrows()}
    res = Servicio().evaluar_sesion(a.child_id, int(sub["edad_meses"].iloc[0]), fotos, a.nombre)
    print(res["informe_docente_md"])
    print("\n--- PANEL TÉCNICO ---")
    print(res["panel_tecnico"]["resumen"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
