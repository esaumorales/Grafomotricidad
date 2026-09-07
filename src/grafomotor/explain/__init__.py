"""
Capa de explicación. LO CENTRAL DEL PROYECTO.

Convierte los valores SHAP + los indicadores geométricos en:
  - un INFORME EN LENGUAJE NATURAL para el docente (sin tecnicismos, con ejemplos y
    sugerencias de actividad),
  - un PANEL TÉCNICO aparte (cifras, T, percentil, tabla SHAP) para el especialista.
"""
from grafomotor.explain.plain_language import explicar_para_docente, Hallazgo
from grafomotor.explain.report import construir_informe, InformeCompleto
from grafomotor.explain.shap_values import shap_por_sesion

__all__ = [
    "explicar_para_docente", "Hallazgo",
    "construir_informe", "InformeCompleto",
    "shap_por_sesion",
]
