"""
Capa de explicación. LO CENTRAL DEL PROYECTO.

Convierte los valores SHAP + los indicadores geométricos en:
  - un INFORME EN LENGUAJE NATURAL para el docente (sin tecnicismos, con ejemplos y
    sugerencias de actividad),
  - un PANEL TÉCNICO aparte (cifras, T, percentil, tabla SHAP) para el especialista.
"""
from grafomotor.explain.plain_language import Hallazgo, explicar_para_docente
from grafomotor.explain.report import InformeCompleto, construir_informe
from grafomotor.explain.shap_values import shap_por_sesion

__all__ = [
    "Hallazgo",
    "InformeCompleto",
    "construir_informe",
    "explicar_para_docente",
    "shap_por_sesion",
]
