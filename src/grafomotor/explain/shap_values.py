"""Cálculo de valores SHAP por figura y agregación por sesión."""
from __future__ import annotations

import numpy as np

from grafomotor import ORDEN
from grafomotor.model.columnas import indicador_de


def shap_por_sesion(modelo, X_figuras: np.ndarray, feature_names: list[str]) -> dict:
    """
    Devuelve:
      por_figura : list[dict]  contribución de cada indicador a cada figura (con signo)
      agg_signed : dict        media con signo por indicador  (negativo = empujó a "incorrecta")
      agg_abs    : dict        media del valor absoluto (magnitud de la influencia)
      base_value : float       valor base del explicador (log-odds)
      columnas   : list[dict]  contribución de cada columna de entrada (panel técnico)

    Las medidas crudas (raw_*) se suman a su indicador: los valores SHAP son aditivos, así
    que la suma es la contribución del indicador completo. Las columnas de figura (fig_*)
    no describen el dibujo del niño y quedan fuera de los indicadores.
    """
    import shap

    # ModeloConUmbral: SHAP sobre el XGBoost; el desplazamiento solo mueve el valor base
    base_modelo = getattr(modelo, "base", modelo)
    if hasattr(base_modelo, "named_steps"):      # modelo final: imputador + Random Forest
        previo = base_modelo[:-1]
        X_figuras = previo.transform(X_figuras)
        # el imputador descarta las columnas vacías en el entrenamiento: quedan menos que las de entrada
        feature_names = list(previo.get_feature_names_out(np.array(feature_names)))
        base_modelo = base_modelo[-1]
    explainer = shap.TreeExplainer(base_modelo)
    sv = explainer.shap_values(X_figuras)
    if isinstance(sv, list):        # algunas versiones devuelven [clase0, clase1]
        sv = sv[1]
    sv = np.asarray(sv, dtype=float)
    if sv.ndim == 3:                # Random Forest: (figuras, columnas, clases) -> clase "correcta"
        sv = sv[:, :, 1]

    columnas = [dict(zip(feature_names, row, strict=True)) for row in sv]
    indicadores = [i for i in ORDEN if any(indicador_de(f) == i for f in feature_names)]
    por_figura = [
        {i: float(sum(v for f, v in c.items() if indicador_de(f) == i)) for i in indicadores}
        for c in columnas
    ]
    agg_signed = {i: float(np.mean([pf[i] for pf in por_figura])) for i in indicadores}
    agg_abs = {i: float(np.mean([abs(pf[i]) for pf in por_figura])) for i in indicadores}
    base = np.ravel(explainer.expected_value)
    base = float(base[1]) if len(base) > 1 else float(base[0])
    base += float(getattr(modelo, "desplazamiento", 0.0))
    return {
        "por_figura": por_figura,
        "agg_signed": agg_signed,
        "agg_abs": agg_abs,
        "base_value": base,
        "columnas": columnas,
    }
