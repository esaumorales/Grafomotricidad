"""
Paso 09: modelo A vs una variante del modelo B, con los mismos niños, etiquetas y
particiones. Salidas: comparacion_<variante>.json y .md (tabla lista para el artículo).
"""
from __future__ import annotations

import argparse
from collections.abc import Callable

import pandas as pd

from grafomotor.artefactos import Artefactos
from grafomotor.config import Config
from grafomotor.evaluation.comparacion import comparar
from grafomotor.evaluation.reporte import evaluar_oof, validar_oof
from grafomotor.io import guardar_json
from grafomotor.logs import obtener_logger
from grafomotor.scoring.baremo import cargar_baremo

AYUDA = "compara el modelo A con una variante de B (métricas, McNemar+Holm, bootstrap)"
log = obtener_logger(__name__)

FILAS_TABLA: list[tuple[str, Callable[[dict], object]]] = [
    ("Kappa de Cohen (por figura)", lambda r: r["por_figura"]["global"]["kappa"]),
    ("Exactitud balanceada", lambda r: r["por_figura"]["global"]["exactitud_balanceada"]),
    ("F1 macro", lambda r: r["por_figura"]["global"]["f1_macro"]),
    ("Sensibilidad", lambda r: r["por_figura"]["global"]["sensibilidad"]),
    ("Especificidad", lambda r: r["por_figura"]["global"]["especificidad"]),
    ("CCI de la PD completa", lambda r: r["PD_completa"]["cci_acuerdo_absoluto"]),
    ("Bland-Altman: sesgo de la PD", lambda r: r["PD_completa"]["bland_altman"]["sesgo"]),
    ("Bland-Altman: límites 95 %", lambda r: "[{}, {}]".format(
        r["PD_completa"]["bland_altman"]["limite_inferior"],
        r["PD_completa"]["bland_altman"]["limite_superior"])),
    ("Kappa ponderado del nivel",
     lambda r: r["PD_completa"]["nivel"]["kappa_ponderado_cuadratico"]),
    ("CCI de la PD del manual (regla 4 fallos)",
     lambda r: r["PD_manual_regla_4_fallos"]["cci_acuerdo_absoluto"]),
    ("Tasa de fallos (fotos no medidas)", lambda r: r["tasa_fallos"]),
]


def agregar_argumentos(p: argparse.ArgumentParser) -> None:
    p.add_argument("--arq", default=None,
                   help="variante de B (p. ej. resnet18, resnet18_robusto); por defecto config")


def tabla_markdown(rep_a: dict, rep_b: dict, comp: dict, variante: str) -> str:
    lin = [f"| Métrica | A: indicadores + XGBoost | B: {variante} |", "|---|---|---|"]
    lin += [f"| {n} | {f(rep_a)} | {f(rep_b)} |" for n, f in FILAS_TABLA]
    lin += ["", "**Por edad (kappa por figura)**", "", "| Edad | A | B |", "|---|---|---|"]
    for edad, m in rep_a["por_edad"]["figura"].items():
        mb = rep_b["por_edad"]["figura"].get(edad, {})
        lin.append(f"| {edad.replace('_anios', ' años')} | {m['kappa']} | "
                   f"{mb.get('kappa', '—')} |")
    b = comp["bootstrap"]
    lin += ["", "**Diferencias B − A (bootstrap por niño, IC 95 %)**", "",
            (f"- Kappa por figura: {b['kappa_figura']['diferencia_B_menos_A']} "
             f"{b['kappa_figura']['ic95']}"),
            f"- CCI de la PD: {b['cci_PD']['diferencia_B_menos_A']} {b['cci_PD']['ic95']}",
            "", "**McNemar exacto por figura**", "",
            "| Figura | solo A acierta | solo B acierta | p | p (Holm) |",
            "|---|---|---|---|---|"]
    for fig, m in comp["mcnemar"].items():
        lin.append(f"| {fig} | {m['solo_A_acierta']} | {m['solo_B_acierta']} | "
                   f"{m['p_valor']} | {m.get('p_holm', '—')} |")
    return "\n".join(lin)


def ejecutar(args: argparse.Namespace, cfg: Config) -> int:
    art = Artefactos.de_config(cfg)
    variante = args.arq or cfg.get("dl", "arquitectura", default="resnet18")
    oof_a = validar_oof(pd.read_parquet(art.oof_ml))
    oof_b = validar_oof(pd.read_parquet(art.oof_dl(variante)))

    folds = oof_a.merge(oof_b, on=["child_id", "figura_id"], how="outer", suffixes=("_A", "_B"))
    if not (folds["fold_A"] == folds["fold_B"]).all():
        log.error("A y B no usaron las mismas particiones: vuelve a correr "
                  "`grafomotor evaluar-ml` y `grafomotor entrenar-dl`")
        return 1

    baremo = cargar_baremo(cfg.ruta("baremos"))
    n_clases = int(cfg.get("scoring", "n_clases", default=2))
    rep_a, rep_b = evaluar_oof(oof_a, baremo, n_clases), evaluar_oof(oof_b, baremo, n_clases)
    comp = comparar(oof_a, oof_b, int(cfg.get("comparacion", "n_boot", default=2000)))

    guardar_json({"A_xgboost": rep_a, f"B_{variante}": rep_b, "comparacion": comp},
                 art.comparacion(variante))
    md = tabla_markdown(rep_a, rep_b, comp, variante)
    art.comparacion(variante, "md").write_text(md, encoding="utf-8")
    print(md)
    log.info("-> %s", art.comparacion(variante))
    return 0
