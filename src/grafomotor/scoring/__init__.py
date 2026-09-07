"""Scoring: figuras 0/1 -> PD -> (baremo por edad) -> T -> nivel de desempeño."""
from grafomotor.scoring.baremo import tramo_de_edad, pd_a_T, cargar_baremo
from grafomotor.scoring.niveles import nivel_desde_T, NivelResultado

__all__ = ["tramo_de_edad", "pd_a_T", "cargar_baremo", "nivel_desde_T", "NivelResultado"]
