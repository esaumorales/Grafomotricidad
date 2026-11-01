"""Edad en meses completos a la fecha de la evaluación (la que usa la Tabla B.9 del baremo)."""
from __future__ import annotations

from datetime import date

from grafomotor.io import EDAD_MAX_MESES, EDAD_MIN_MESES


def edad_en_meses(nacimiento: date, evaluacion: date) -> int:
    """Meses cumplidos: 2/9/2020 evaluado el 26/9/2026 -> 72 (cumple el mes el día 2, no el 26)."""
    if evaluacion < nacimiento:
        raise ValueError("La fecha de evaluación es anterior a la fecha de nacimiento.")
    meses = (evaluacion.year - nacimiento.year) * 12 + evaluacion.month - nacimiento.month
    return meses - (1 if evaluacion.day < nacimiento.day else 0)


def edad_valida(meses: int) -> bool:
    return EDAD_MIN_MESES <= meses <= EDAD_MAX_MESES
