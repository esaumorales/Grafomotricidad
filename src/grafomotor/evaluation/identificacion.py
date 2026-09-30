"""
IDENTIFICACIÓN de niños en riesgo (tamizaje), además de la evaluación figura por figura.

La decisión es por niño. Con las 15 probabilidades calibradas de sus figuras, su PD es
una variable aleatoria de Poisson-binomial: se calcula exactamente la probabilidad de que
la PD quede en la zona de riesgo de su edad (T <= corte). Así, un error suelto en una
figura no decide por sí solo, y los casos dudosos se reconocen como tales.

Triaje en tres zonas (umbrales en config.yaml > identificacion):

    P(riesgo) >= umbral_alto   ->  "en riesgo"      (derivar / reforzar)
    P(riesgo) <= umbral_bajo   ->  "adecuado"
    entre ambos                ->  "revisar"        (lo decide un evaluador humano)

En tamizaje el error grave es NO detectar a un niño en riesgo: se reportan sensibilidad y
valor predictivo negativo con IC de Wilson, y cuántos niños se derivan a revisión.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from grafomotor.scoring.baremo import pd_a_T

N_FIGURAS_MAX = 15


def distribucion_pd(probs) -> np.ndarray:
    """P(PD = k), k = 0..n, para figuras independientes con prob. de acierto `probs`."""
    dist = np.array([1.0])
    for p in probs:
        dist = np.convolve(dist, [1 - p, p])
    return dist


def pd_maxima_en_riesgo(edad_meses: int, baremo: pd.DataFrame, corte_T: float,
                        n_figuras: int = N_FIGURAS_MAX) -> int:
    """La PD más alta que a esa edad todavía queda en riesgo (T <= corte). -1 si ninguna."""
    en_riesgo = [pd_ for pd_ in range(n_figuras + 1)
                 if pd_a_T(pd_, edad_meses, baremo)["T"] <= corte_T]
    return max(en_riesgo) if en_riesgo else -1


def wilson(aciertos: int, n: int, z: float = 1.96) -> list[float]:
    """IC 95 % de Wilson para una proporción (mejor que el de Wald con n pequeño)."""
    if n == 0:
        return [float("nan"), float("nan")]
    p = aciertos / n
    centro = (p + z * z / (2 * n)) / (1 + z * z / n)
    margen = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(float(centro - margen), 3), round(float(centro + margen), 3)]


def tabla_ninos(oof: pd.DataFrame, baremo: pd.DataFrame, corte_T: float,
                col_prob: str = "prob_cal") -> pd.DataFrame:
    """Por niño: riesgo real (experto), P(riesgo) del modelo y PD esperada."""
    filas = []
    for cid, g in oof.groupby("child_id"):
        edad = int(g["edad_meses"].iloc[0])
        corte_pd = pd_maxima_en_riesgo(edad, baremo, corte_T)
        # figura no medida -> se trata como 0 (criterio conservador, igual que en la PD)
        probs = g[col_prob].fillna(0.0).to_numpy()
        dist = distribucion_pd(probs)
        filas.append({
            "child_id": cid, "edad_meses": edad, "pd_corte_riesgo": corte_pd,
            "PD_experto": int(g["y"].sum()),
            "riesgo_real": int(g["y"].sum() <= corte_pd),
            "PD_esperada": round(float(probs.sum()), 2),
            "p_riesgo": round(float(dist[: corte_pd + 1].sum()) if corte_pd >= 0 else 0.0, 4),
        })
    return pd.DataFrame(filas)


def metricas_tamizaje(real, positivo) -> dict:
    real, positivo = np.asarray(real, int), np.asarray(positivo, int)
    vp = int(((real == 1) & (positivo == 1)).sum())
    fn = int(((real == 1) & (positivo == 0)).sum())
    vn = int(((real == 0) & (positivo == 0)).sum())
    fp = int(((real == 0) & (positivo == 1)).sum())

    def _prop(a, n):
        return {"valor": round(a / n, 3) if n else float("nan"), "ic95": wilson(a, n), "n": n}

    return {"sensibilidad": _prop(vp, vp + fn), "especificidad": _prop(vn, vn + fp),
            "VPP": _prop(vp, vp + fp), "VPN": _prop(vn, vn + fn),
            "confusion": {"VP": vp, "FN": fn, "VN": vn, "FP": fp}}


def triaje(ninos: pd.DataFrame, umbral_bajo: float, umbral_alto: float) -> dict:
    """Tres zonas: se decide solo fuera de la zona gris; dentro, revisión humana."""
    p = ninos["p_riesgo"]
    zona = np.where(p >= umbral_alto, "en_riesgo", np.where(p <= umbral_bajo, "adecuado",
                                                            "revisar"))
    decididos = zona != "revisar"
    real = ninos["riesgo_real"].to_numpy()
    return {
        "umbrales": {"bajo": umbral_bajo, "alto": umbral_alto},
        "n_ninos": len(ninos),
        "a_revision": {"n": int((~decididos).sum()),
                       "fraccion": round(float((~decididos).mean()), 3),
                       "de_ellos_en_riesgo_real": int(real[~decididos].sum())},
        # sobre los decididos automáticamente
        "decididos_automaticamente": metricas_tamizaje(real[decididos],
                                                       (zona[decididos] == "en_riesgo")),
        # peor caso: niños en riesgo que el sistema dio por "adecuados" sin revisión
        "en_riesgo_no_detectados": int(((zona == "adecuado") & (real == 1)).sum()),
    }


def evaluar_identificacion(oof: pd.DataFrame, baremo: pd.DataFrame, corte_T: float,
                           umbral_bajo: float, umbral_alto: float) -> dict:
    ninos = tabla_ninos(oof, baremo, corte_T)
    real = ninos["riesgo_real"]
    auc = (round(float(roc_auc_score(real, ninos["p_riesgo"])), 3)
           if real.nunique() == 2 else float("nan"))
    return {
        "corte_T": corte_T,
        "prevalencia_riesgo": round(float(real.mean()), 3),
        "auc_p_riesgo": auc,
        "sin_zona_gris_umbral_0.5": metricas_tamizaje(real, ninos["p_riesgo"] >= 0.5),
        "triaje": triaje(ninos, umbral_bajo, umbral_alto),
    }, ninos


def curva_selectiva(oof: pd.DataFrame, col_prob: str = "prob_cal",
                    coberturas=(1.0, 0.9, 0.8, 0.7, 0.6, 0.5)) -> list[dict]:
    """EVALUACIÓN selectiva por figura: si solo se califican solas las figuras en que el
    modelo está más seguro, ¿cuánto sube el kappa? El resto iría a revisión humana."""
    from sklearn.metrics import cohen_kappa_score

    med = oof[oof[col_prob].notna()].copy()
    med["confianza"] = (med[col_prob] - 0.5).abs()
    med = med.sort_values("confianza", ascending=False)
    salida = []
    for c in coberturas:
        top = med.head(max(1, round(c * len(med))))
        yhat = (top[col_prob] >= 0.5).astype(int)
        kappa = (cohen_kappa_score(top["y"], yhat)
                 if top["y"].nunique() == 2 and yhat.nunique() == 2 else float("nan"))
        salida.append({"cobertura": c, "n": len(top),
                       "kappa": round(float(kappa), 3),
                       "exactitud": round(float((yhat == top["y"]).mean()), 3),
                       "confianza_minima": round(float(top["confianza"].min() + 0.5), 3)})
    return salida
