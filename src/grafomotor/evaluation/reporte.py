"""
Reporte completo de UN modelo a partir de sus predicciones out-of-fold.

Entrada común a los dos modelos (data/processed/oof_<modelo>.parquet):

    child_id, figura_id, edad_meses, fold, y (experto 0/1), yhat (0/1, NaN = fallo), prob

`yhat` es NaN cuando la foto no se pudo medir (p. ej. el registro con la plantilla no
convergió en el modelo A). Esas filas cuentan en la tasa de fallos; las métricas por
figura se calculan sobre las medidas, y para la PD se cuentan como 0 (criterio
conservador, igual que una figura no puntuada).
"""
from __future__ import annotations

import pandas as pd

from grafomotor.evaluation.metrics import (
    bland_altman,
    icc_acuerdo_absoluto,
    metricas_nivel,
    metricas_por_figura,
)
from grafomotor.evaluation.stratified import edad_en_anios, estratificar_por_edad
from grafomotor.scoring.baremo import pd_a_T
from grafomotor.scoring.niveles import nivel_desde_T
from grafomotor.scoring.pd import pd_completa, pd_manual

COLUMNAS_OOF = ["child_id", "figura_id", "edad_meses", "fold", "y", "yhat", "prob"]


def etiquetas_nivel(n_clases: int) -> list[str]:
    return ["Adecuado", "En riesgo"] if n_clases == 2 else ["Adecuado", "Bajo", "Muy bajo"]


def tabla_por_nino(oof: pd.DataFrame, baremo: pd.DataFrame, n_clases: int = 2) -> pd.DataFrame:
    """Una fila por niño: PD completa y del manual (experto y modelo) y nivel."""
    filas = []
    for cid, g in oof.groupby("child_id"):
        g = g.sort_values("figura_id")
        edad = int(g["edad_meses"].iloc[0])
        y = dict(zip(g["figura_id"], g["y"].astype(int), strict=True))
        yhat = dict(zip(g["figura_id"], g["yhat"].fillna(0).astype(int), strict=True))
        fila = {"child_id": cid, "edad_meses": edad}
        for nombre, fn in (("completa", pd_completa), ("manual", pd_manual)):
            pr, pp = fn(y), fn(yhat)
            fila[f"PD_{nombre}_experto"], fila[f"PD_{nombre}_modelo"] = pr, pp
            for quien, valor in (("experto", pr), ("modelo", pp)):
                T = pd_a_T(valor, edad, baremo)["T"]
                fila[f"nivel_{nombre}_{quien}"] = nivel_desde_T(T, n_clases).nivel
        filas.append(fila)
    return pd.DataFrame(filas)


def _bloque_pd(ninos: pd.DataFrame, variante: str, n_clases: int) -> dict:
    a, b = ninos[f"PD_{variante}_experto"], ninos[f"PD_{variante}_modelo"]
    return {
        "cci_acuerdo_absoluto": icc_acuerdo_absoluto(a, b),
        "bland_altman": bland_altman(a, b),
        "nivel": metricas_nivel(ninos[f"nivel_{variante}_experto"],
                                ninos[f"nivel_{variante}_modelo"], etiquetas_nivel(n_clases)),
    }


def evaluar_oof(oof: pd.DataFrame, baremo: pd.DataFrame, n_clases: int = 2) -> dict:
    faltan = [c for c in COLUMNAS_OOF if c not in oof.columns]
    if faltan:
        raise ValueError(f"predicciones OOF sin columnas {faltan}")
    medidas = oof[oof["yhat"].notna()]
    y, yhat = medidas["y"].astype(int), medidas["yhat"].astype(int)
    ninos = tabla_por_nino(oof, baremo, n_clases)

    por_edad_pd = {}
    anios = edad_en_anios(ninos["edad_meses"])
    for a in sorted(set(anios)):
        sub = ninos[anios == a]
        por_edad_pd[f"{a}_anios"] = {
            "n_ninos": len(sub),
            "cci_PD_completa": icc_acuerdo_absoluto(sub["PD_completa_experto"],
                                                    sub["PD_completa_modelo"]),
            "bland_altman_PD_completa": bland_altman(sub["PD_completa_experto"],
                                                     sub["PD_completa_modelo"]),
        }

    return {
        "n_ninos": int(oof["child_id"].nunique()),
        "n_figuras": len(oof),
        "tasa_fallos": round(float(oof["yhat"].isna().mean()), 4),
        "por_figura": metricas_por_figura(y, yhat, medidas["figura_id"]),
        "por_edad": {
            "figura": estratificar_por_edad(y, yhat, medidas["edad_meses"]),
            "PD": por_edad_pd,
        },
        "PD_completa": _bloque_pd(ninos, "completa", n_clases),
        "PD_manual_regla_4_fallos": _bloque_pd(ninos, "manual", n_clases),
    }


def validar_oof(oof: pd.DataFrame) -> pd.DataFrame:
    """Normaliza tipos y comprueba que no haya filas duplicadas."""
    oof = oof.copy()
    oof["y"] = oof["y"].astype(int)
    oof["yhat"] = oof["yhat"].astype(float)
    if oof.duplicated(["child_id", "figura_id"]).any():
        raise ValueError("predicciones OOF con (child_id, figura_id) duplicados")
    return oof


def resumen_corto(rep: dict) -> dict:
    """Las cifras principales, para imprimir en consola."""
    g = rep["por_figura"]["global"]
    return {
        "kappa_figura": g["kappa"], "exactitud_balanceada": g["exactitud_balanceada"],
        "f1_macro": g["f1_macro"], "sensibilidad": g["sensibilidad"],
        "especificidad": g["especificidad"],
        "cci_PD": rep["PD_completa"]["cci_acuerdo_absoluto"],
        "sesgo_PD": rep["PD_completa"]["bland_altman"]["sesgo"],
        "kappa_pond_nivel": rep["PD_completa"]["nivel"]["kappa_ponderado_cuadratico"],
        "tasa_fallos": rep["tasa_fallos"],
    }


__all__ = [
    "COLUMNAS_OOF",
    "etiquetas_nivel",
    "evaluar_oof",
    "resumen_corto",
    "tabla_por_nino",
    "validar_oof",
]
