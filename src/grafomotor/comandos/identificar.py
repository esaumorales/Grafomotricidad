"""
Paso 17: IDENTIFICACIÓN de niños en riesgo y EVALUACIÓN selectiva, para A o una variante de B.

  grafomotor identificar                    modelo A
  grafomotor identificar --arq resnet18     una variante de B

1. Calibra las probabilidades por figura (Platt cruzado, sin mirar el fold calibrado).
2. Identificación por niño: P(riesgo) exacta con la distribución de la PD; sensibilidad,
   especificidad, VPP y VPN con IC de Wilson; triaje con zona gris a revisión humana.
3. Evaluación selectiva por figura: kappa si solo se califican solas las más seguras.

Los umbrales de la zona gris se fijan de antemano en config.yaml (no se eligen mirando
estas cifras). Salidas: identificacion_<modelo>.json y .md
"""
from __future__ import annotations

import argparse

import pandas as pd

from grafomotor.artefactos import Artefactos
from grafomotor.config import Config
from grafomotor.evaluation.calibracion import error_calibracion, platt_cruzado
from grafomotor.evaluation.identificacion import curva_selectiva, evaluar_identificacion
from grafomotor.io import guardar_json
from grafomotor.logs import obtener_logger
from grafomotor.scoring.baremo import cargar_baremo

AYUDA = "identificación de niños en riesgo (con zona gris) y evaluación selectiva por figura"
log = obtener_logger(__name__)


def agregar_argumentos(p: argparse.ArgumentParser) -> None:
    p.add_argument("--arq", default=None, help="variante de B; sin esto, el modelo A")


def a_markdown(nombre: str, rep: dict) -> str:
    t, s = rep["triaje"], rep["sin_zona_gris_umbral_0.5"]
    auto = t["decididos_automaticamente"]

    def f(m):
        return f"{m['valor']} {m['ic95']}"

    lin = [f"## Identificación de niños en riesgo — {nombre}", "",
           f"Prevalencia de riesgo (experto): {rep['prevalencia_riesgo']} · "
           f"AUC de P(riesgo): {rep['auc_p_riesgo']}", "",
           "| | Sin zona gris (P ≥ 0.5) | Con triaje (solo decididos) |", "|---|---|---|"]
    for m in ("sensibilidad", "especificidad", "VPP", "VPN"):
        lin.append(f"| {m} | {f(s[m])} | {f(auto[m])} |")
    lin += ["", f"- A revisión humana: {t['a_revision']['n']} de {t['n_ninos']} niños "
                f"({100 * t['a_revision']['fraccion']:.0f} %), de ellos "
                f"{t['a_revision']['de_ellos_en_riesgo_real']} en riesgo real.",
            f"- Niños en riesgo dados por adecuados sin revisión: "
            f"**{t['en_riesgo_no_detectados']}**.",
            f"- Zona gris: {t['umbrales']['bajo']} < P(riesgo) < {t['umbrales']['alto']}.", "",
            "## Evaluación selectiva por figura", "",
            "| Cobertura (se califican solas) | κ | exactitud | confianza mínima |",
            "|---|---|---|---|"]
    lin += [f"| {int(100 * c['cobertura'])} % | {c['kappa']} | {c['exactitud']} | "
            f"{c['confianza_minima']} |" for c in rep["evaluacion_selectiva"]]
    cal = rep["calibracion"]
    lin += ["", f"Calibración (Brier / ECE): antes {cal['antes']['brier']} / {cal['antes']['ece']}"
                f" · después {cal['despues']['brier']} / {cal['despues']['ece']}"]
    return "\n".join(lin)


def ejecutar(args: argparse.Namespace, cfg: Config) -> int:
    art = Artefactos.de_config(cfg)
    nombre = args.arq or "ml"
    oof = pd.read_parquet(art.oof_dl(args.arq) if args.arq else art.oof_ml)
    oof["prob_cal"] = platt_cruzado(oof)

    cfg_i = cfg.get("identificacion", default={})
    corte = float(cfg.get("scoring", "corte_bajo_T", default=40))
    rep, ninos = evaluar_identificacion(oof, cargar_baremo(cfg.ruta("baremos")), corte,
                                        float(cfg_i.get("umbral_bajo", 0.2)),
                                        float(cfg_i.get("umbral_alto", 0.8)))
    rep["calibracion"] = {"metodo": "Platt cruzado por fold",
                          "antes": error_calibracion(oof["y"], oof["prob"]),
                          "despues": error_calibracion(oof["y"], oof["prob_cal"])}
    # la evaluación por figura usa las decisiones originales del modelo (su 100 % coincide
    # con el kappa del resto del reporte); la calibración es para la identificación por niño
    rep["evaluacion_selectiva"] = curva_selectiva(oof, col_prob="prob")

    guardar_json(rep, art.identificacion(nombre))
    ninos.to_csv(art.identificacion(nombre, "csv"), index=False)
    md = a_markdown(nombre, rep)
    art.identificacion(nombre, "md").write_text(md, encoding="utf-8")
    print(md)
    return 0
