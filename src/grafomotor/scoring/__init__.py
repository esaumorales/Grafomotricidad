"""Scoring: figuras 0/1 -> PD -> (baremo por edad) -> percentil -> nivel de desempeño."""
from grafomotor.scoring.baremo import cargar_baremo, pd_a_percentil, pd_a_T, tramo_de_edad
from grafomotor.scoring.niveles import (
    CriterioNiveles, NivelResultado, nivel_desde_percentil, nivel_desde_T,
)

__all__ = ["CriterioNiveles", "NivelResultado", "cargar_baremo", "nivel_desde_percentil",
           "nivel_desde_T", "pd_a_percentil", "pd_a_T", "tramo_de_edad"]
