"""
Paso 13: tabla de TODAS las variantes de B frente a A, para elegir la que pasa al artículo.

  grafomotor resumen-variantes
  grafomotor resumen-variantes --versus resnet18_robusto efficientnet_b0_robusto
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from grafomotor.artefactos import Artefactos
from grafomotor.config import Config
from grafomotor.evaluation.comparacion import comparar
from grafomotor.evaluation.reporte import resumen_corto, validar_oof
from grafomotor.io import leer_json
from grafomotor.logs import obtener_logger

AYUDA = "resume todas las variantes de B frente a A (y compara dos variantes con --versus)"
log = obtener_logger(__name__)

COLUMNAS = ["variante", "kappa_figura", "exactitud_balanceada", "f1_macro", "cci_PD",
            "sesgo_PD", "kappa_pond_nivel", "peor_cci_degradado"]


def agregar_argumentos(p: argparse.ArgumentParser) -> None:
    p.add_argument("--versus", nargs=2, metavar=("V1", "V2"), default=None,
                   help="compara dos variantes de B entre sí (McNemar + bootstrap)")


def peor_robustez(robustez: dict, modelo: str) -> str:
    """El CCI de la PD más bajo entre las degradaciones sintéticas, con su condición."""
    degr = robustez.get("degradaciones", {})
    if not degr:
        return "—"
    cond = min(degr, key=lambda c: degr[c][modelo]["cci_PD"])
    return f"{degr[cond][modelo]['cci_PD']} ({cond})"


def filas_tabla(art: Artefactos) -> list[dict]:
    filas = []
    robusteces = sorted(art.procesados.glob("robustez_*.json"))
    if art.evaluacion_ml.exists():
        fila = {"variante": "A_xgboost", **resumen_corto(leer_json(art.evaluacion_ml))}
        if robusteces:   # A es igual en todos los archivos de robustez (misma caché)
            fila["peor_cci_degradado"] = peor_robustez(leer_json(robusteces[0]), "A")
        filas.append(fila)

    if art.acuerdo_evaluadores.exists():
        filas.append({"variante": "techo humano (2 evaluadores)",
                      **resumen_corto(leer_json(art.acuerdo_evaluadores))})

    for v in art.variantes_dl():
        fila = {"variante": v, **resumen_corto(leer_json(art.evaluacion_dl(v)))}
        if art.variabilidad_dl(v).exists():
            r = leer_json(art.variabilidad_dl(v))["resumen"]
            for m in ("kappa_figura", "cci_PD"):
                fila[m] = f"{r[m]['media']} ± {r[m]['de']}"
        if art.robustez(v).exists():
            fila["peor_cci_degradado"] = peor_robustez(leer_json(art.robustez(v)), "B")
        filas.append(fila)
    return filas


def a_markdown(df: pd.DataFrame) -> list[str]:
    md = ["| " + " | ".join(df.columns) + " |", "|" + "---|" * len(df.columns)]
    md += ["| " + " | ".join(str(x) for x in fila) + " |" for fila in df.itertuples(index=False)]
    return md


def ejecutar(args: argparse.Namespace, cfg: Config) -> int:
    art = Artefactos.de_config(cfg)
    df = pd.DataFrame(filas_tabla(art))
    if df.empty:
        log.error("no hay evaluaciones en %s", art.procesados)
        return 1
    df = df[[c for c in COLUMNAS if c in df.columns]].replace({np.nan: "—"})
    md = [*a_markdown(df),
          "", "_Con --semillas, kappa y CCI se muestran como media ± DE entre semillas._",
          "_peor_cci_degradado: el CCI de la PD más bajo entre las degradaciones sintéticas._"]

    if args.versus:
        v1, v2 = args.versus
        c = comparar(validar_oof(pd.read_parquet(art.oof_dl(v1))),
                     validar_oof(pd.read_parquet(art.oof_dl(v2))),
                     int(cfg.get("comparacion", "n_boot", default=2000)))
        b, g = c["bootstrap"], c["mcnemar"]["global"]
        md += ["", f"**{v2} − {v1}** (bootstrap por niño, IC 95 %)", "",
               (f"- Kappa por figura: {b['kappa_figura']['diferencia_B_menos_A']} "
                f"{b['kappa_figura']['ic95']}"),
               f"- CCI de la PD: {b['cci_PD']['diferencia_B_menos_A']} {b['cci_PD']['ic95']}",
               (f"- McNemar global: solo {v1} acierta {g['solo_A_acierta']}, "
                f"solo {v2} acierta {g['solo_B_acierta']}, p = {g['p_valor']}")]

    texto = "\n".join(md)
    art.resumen_variantes.write_text(texto, encoding="utf-8")
    print(texto)
    return 0
