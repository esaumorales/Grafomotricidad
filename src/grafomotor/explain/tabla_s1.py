"""
Tabla S1 del artículo: qué indicadores miden los criterios del manual en cada figura.

Se fijó con la psicóloga ANTES de calcular SHAP (la genera
experimentos/articulo_103e/material_suplementario.py). La aplicación la usa para que el informe
a la docente solo dé como razón de una figura lo que el manual revisa en ESA figura (p. ej. el
cierre en el círculo, nunca en la línea recta). Generado desde tabla_s1.json: no editar a mano.
"""
from __future__ import annotations

# indicador (concepto de la Tabla S1) -> columnas del modelo que lo miden
COLUMNAS_POR_INDICADOR: dict[str, list[str]] = {
    'Similitud con el modelo': ['precision_modelo', 'raw_iou'],
    'Número de vértices': ['vertices', 'raw_n_vertices'],
    'Error angular': ['error_angular', 'raw_error_angular_deg', 'dif_angulo'],
    'Índice de cierre': ['cierre', 'raw_extremos_libres', 'cr_extremos', 'dif_extremos'],
    'Error en los puntos de intersección': ['intersecciones', 'raw_dist_interseccion_px'],
    'Número de partes': ['cr_partes', 'dif_partes'],
    'Contacto entre partes': ['cr_partes_juntas', 'dif_partes_juntas', 'cr_dist_partes', 'dif_dist_partes'],
    'Cruces': ['cr_cruces', 'dif_cruces'],
    'Ondulaciones': ['cr_ondas', 'dif_ondas'],
    'Esquinas': ['cr_esquinas', 'dif_esquinas'],
    'Giro máximo': ['cr_giro_max', 'dif_giro_max'],
    'Inclinación': ['cr_incl_partes', 'dif_incl_partes'],
}

# figura -> indicadores que miden alguno de sus criterios del manual
INDICADORES_POR_FIGURA: dict[str, list[str]] = {
    'F01': ['Error angular', 'Esquinas', 'Giro máximo', 'Inclinación', 'Número de partes', 'Número de vértices', 'Similitud con el modelo'],
    'F02': ['Contacto entre partes', 'Cruces', 'Esquinas', 'Giro máximo', 'Inclinación', 'Número de partes', 'Ondulaciones', 'Similitud con el modelo'],
    'F03': ['Contacto entre partes', 'Cruces', 'Error en los puntos de intersección', 'Esquinas', 'Giro máximo', 'Número de partes', 'Ondulaciones'],
    'F04': ['Error angular', 'Esquinas', 'Giro máximo', 'Número de vértices', 'Índice de cierre'],
    'F05': ['Error angular', 'Esquinas', 'Giro máximo', 'Inclinación', 'Número de vértices', 'Ondulaciones', 'Similitud con el modelo', 'Índice de cierre'],
    'F06': ['Esquinas', 'Giro máximo', 'Número de vértices', 'Ondulaciones', 'Similitud con el modelo', 'Índice de cierre'],
    'F07': ['Cruces', 'Error angular', 'Error en los puntos de intersección', 'Inclinación', 'Número de partes'],
    'F08': ['Contacto entre partes', 'Inclinación', 'Número de partes', 'Ondulaciones', 'Similitud con el modelo'],
    'F09': ['Cruces', 'Error en los puntos de intersección', 'Esquinas', 'Número de vértices', 'Similitud con el modelo', 'Índice de cierre'],
    'F10': ['Esquinas', 'Inclinación', 'Número de vértices', 'Similitud con el modelo', 'Índice de cierre'],
    'F11': ['Contacto entre partes', 'Esquinas', 'Giro máximo', 'Inclinación', 'Número de partes', 'Número de vértices', 'Ondulaciones', 'Similitud con el modelo', 'Índice de cierre'],
    'F12': ['Contacto entre partes', 'Cruces', 'Giro máximo', 'Inclinación', 'Número de partes', 'Ondulaciones', 'Similitud con el modelo'],
    'F13': ['Contacto entre partes', 'Cruces', 'Error en los puntos de intersección', 'Esquinas', 'Giro máximo', 'Inclinación', 'Número de partes', 'Similitud con el modelo'],
    'F14': ['Cruces', 'Error en los puntos de intersección', 'Esquinas', 'Inclinación', 'Número de vértices', 'Ondulaciones', 'Similitud con el modelo'],
    'F15': ['Cruces', 'Error angular', 'Error en los puntos de intersección', 'Esquinas', 'Giro máximo', 'Inclinación', 'Número de vértices', 'Ondulaciones', 'Similitud con el modelo', 'Índice de cierre'],
}

# --- uso en la aplicación (escrito a mano; lo de arriba es la tabla) ------------------------------
_INDICADOR_DE_COLUMNA = {c: k for k, cols in COLUMNAS_POR_INDICADOR.items() for c in cols}

# indicador general que ve la docente -> indicador de la Tabla S1 que mide directamente su valor
GENERAL_A_TABLA = {
    "precision_modelo": "Similitud con el modelo",
    "vertices": "Número de vértices",
    "error_angular": "Error angular",
    "cierre": "Índice de cierre",
    "intersecciones": "Error en los puntos de intersección",
}


def columnas_fuera_del_manual(figura_id: str, columnas: list[str]) -> set[str]:
    """Columnas (también las 'missingindicator_<col>' del imputador) cuyo indicador no mide ningún
    criterio del manual en esa figura. Las que no son de ningún indicador (fig_*) no se tocan."""
    if figura_id not in INDICADORES_POR_FIGURA:
        return set()
    del_manual = set(INDICADORES_POR_FIGURA[figura_id])
    fuera = set()
    for c in columnas:
        k = _INDICADOR_DE_COLUMNA.get(c.removeprefix("missingindicator_"))
        if k is not None and k not in del_manual:
            fuera.add(c)
    return fuera


def aplica(indicador_general: str, figura_id: str) -> bool:
    """¿El manual revisa en esa figura lo que mide ese indicador general? (p. ej. cierre: sí en el
    círculo, no en la línea recta). Si no hay dato para decidirlo, se considera que sí."""
    k = GENERAL_A_TABLA.get(indicador_general)
    if k is None or figura_id not in INDICADORES_POR_FIGURA:
        return True
    return k in INDICADORES_POR_FIGURA[figura_id]
