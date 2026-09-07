"""Cálculo de valores SHAP por figura y agregación por sesión."""
from __future__ import annotations

import numpy as np


def shap_por_sesion(modelo, X_figuras: np.ndarray, feature_names: list[str]) -> dict:
    """
    Devuelve:
      por_figura : list[dict]  contribución de cada indicador a cada figura (con signo)
      agg_signed : dict        media con signo por indicador  (negativo = empujó a "incorrecta")
      agg_abs    : dict        media del valor absoluto (magnitud de la influencia)
      base_value : float       valor base del explicador (log-odds)
    """
    import shap

    explainer = shap.TreeExplainer(modelo)
    sv = explainer.shap_values(X_figuras)
    if isinstance(sv, list):        # algunas versiones devuelven [clase0, clase1]
        sv = sv[1]
    sv = np.asarray(sv, dtype=float)

    por_figura = [dict(zip(feature_names, row)) for row in sv]
    agg_signed = {f: float(np.mean([pf[f] for pf in por_figura])) for f in feature_names}
    agg_abs = {f: float(np.mean([abs(pf[f]) for pf in por_figura])) for f in feature_names}
    base = explainer.expected_value
    base = float(base[1]) if hasattr(base, "__len__") else float(base)
    return {
        "por_figura": por_figura,
        "agg_signed": agg_signed,
        "agg_abs": agg_abs,
        "base_value": base,
    }
