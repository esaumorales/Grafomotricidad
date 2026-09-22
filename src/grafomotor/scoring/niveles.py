"""
Percentil -> nivel de desempeño grafomotor.

Los cortes T>=41/31-40/<=30 que citaba una versión anterior (manual, pág. 98-99)
NO están verificados: el equipo no ha confirmado que esas páginas correspondan a
esta edición del manual ni a la subescala de Visopercepción (ver ESTADO.md).
Mientras esas páginas no se verifiquen, el sistema clasifica directamente sobre
el PERCENTIL, que es el único dato confirmado contra el libro físico (Tabla B.9,
pág. 83 — ver `scoring/baremo.py`).

Los cortes de percentil son la convención estándar en psicometría para definir
bandas de riesgo a partir de una distribución normal (Pc ≈ percentil equivalente
a -1 y -2 desviaciones típicas):

    Pc > 16   -> Adecuado
    Pc 3-16   -> Bajo (en riesgo / screening)   [~ -1 DE]
    Pc <= 2   -> Muy bajo (derivar)              [~ -2 DE]

Si el equipo consigue verificar las páginas 98-99 del manual original, estos
cortes deben sustituirse por los oficiales del CUMANIN (documentar la fuente
exacta al hacerlo).
"""
from __future__ import annotations

from dataclasses import dataclass

CORTE_BAJO_PC = 16
CORTE_MUY_BAJO_PC = 2

# Bandas descriptivas por percentil (convención estándar en psicometría,
# equivalente aprox. a bandas de -2/-1/0/+1/+2 desviaciones típicas).
# NO proviene de una tabla del manual CUMANIN: es una convención general,
# para el panel técnico del especialista.
_BANDAS_DESCRIPTIVAS = [
    ("Muy alto", 98, 100),
    ("Alto", 91, 97),
    ("Medio-alto", 75, 90),
    ("Medio", 25, 74),
    ("Medio-bajo", 9, 24),
    ("Bajo", 3, 8),
    ("Muy bajo", 0, 2),
]


@dataclass
class NivelResultado:
    percentil: float
    nivel: str                 # etiqueta según n_clases
    accion: str                # "ninguna" | "reforzar_y_revaluar" | "derivar"
    descriptor_verbal: str     # banda descriptiva (para el especialista)
    n_clases: int


def descriptor_verbal(percentil: float) -> str:
    for nombre, lo, hi in _BANDAS_DESCRIPTIVAS:
        if lo <= percentil <= hi:
            return nombre
    return "Medio"


def nivel_desde_percentil(percentil: float, n_clases: int = 2,
                           corte_bajo: int = CORTE_BAJO_PC,
                           corte_muy_bajo: int = CORTE_MUY_BAJO_PC) -> NivelResultado:
    if percentil <= corte_muy_bajo:
        accion = "derivar"
    elif percentil <= corte_bajo:
        accion = "reforzar_y_revaluar"
    else:
        accion = "ninguna"

    if n_clases == 3:
        nivel = {"derivar": "Muy bajo", "reforzar_y_revaluar": "Bajo", "ninguna": "Adecuado"}[accion]
    else:
        nivel = "En riesgo" if percentil <= corte_bajo else "Adecuado"

    return NivelResultado(
        percentil=round(float(percentil), 1),
        nivel=nivel,
        accion=accion,
        descriptor_verbal=descriptor_verbal(percentil),
        n_clases=n_clases,
    )
