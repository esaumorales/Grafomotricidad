"""
T -> nivel de desempeño grafomotor, según los puntos de corte del CUMANIN-2
(manual, pág. 98-99):

    T >= 41  -> Adecuado
    31-40    -> Bajo (en riesgo / screening)
    <= 30    -> Muy bajo (derivar a especialista)

`n_clases`:
  2 -> {Adecuado, En riesgo}      (En riesgo = T <= 40; recomendado por defecto)
  3 -> {Adecuado, Bajo, Muy bajo}

Tabla 5.2 (7 descriptores) disponible en `descriptor_verbal()` para el panel técnico.
"""
from __future__ import annotations

from dataclasses import dataclass

CORTE_BAJO = 40
CORTE_MUY_BAJO = 30

# Tabla 5.2 del manual (descriptor -> (T_min, T_max))
TABLA_5_2 = [
    ("Muy alto", 70, 999),
    ("Alto", 60, 69),
    ("Medio-alto", 55, 59),
    ("Medio", 46, 54),
    ("Medio-bajo", 41, 45),
    ("Bajo", 31, 40),
    ("Muy bajo", -999, 30),
]


@dataclass
class NivelResultado:
    T: float
    nivel: str                 # etiqueta según n_clases
    accion: str                # "ninguna" | "reforzar_y_revaluar" | "derivar"
    descriptor_verbal: str     # de la Tabla 5.2 (para el especialista)
    n_clases: int


def descriptor_verbal(T: float) -> str:
    for nombre, lo, hi in TABLA_5_2:
        if lo <= T <= hi:
            return nombre
    return "Medio"


def nivel_desde_T(T: float, n_clases: int = 2,
                  corte_bajo: int = CORTE_BAJO, corte_muy_bajo: int = CORTE_MUY_BAJO) -> NivelResultado:
    if T <= corte_muy_bajo:
        accion = "derivar"
    elif T <= corte_bajo:
        accion = "reforzar_y_revaluar"
    else:
        accion = "ninguna"

    if n_clases == 3:
        nivel = {"derivar": "Muy bajo", "reforzar_y_revaluar": "Bajo", "ninguna": "Adecuado"}[accion]
    else:
        nivel = "En riesgo" if T <= corte_bajo else "Adecuado"

    return NivelResultado(
        T=round(float(T), 1),
        nivel=nivel,
        accion=accion,
        descriptor_verbal=descriptor_verbal(T),
        n_clases=n_clases,
    )
