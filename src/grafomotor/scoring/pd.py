"""
Puntuación Directa (PD) de la Visopercepción: dos variantes.

En la aplicación grupal todos los niños copian las 15 figuras (no se aplica la regla
de parada). Por eso se guardan las 15 puntuaciones y se calculan dos PD:

  - PD completa: suma de las 15 figuras.
  - PD del manual: se aplica la regla de parada de forma retrospectiva; tras
    `n_fallos` ceros SEGUIDOS (en el orden F01..F15) las figuras siguientes no
    cuentan, aunque el niño las haya acertado.

Cuál de las dos es la oficial para el estudio está pendiente con el asesor.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

N_FALLOS_PARADA = 4


def _ordenar(puntajes: Mapping[str, int] | Sequence[int]) -> list[int]:
    if isinstance(puntajes, Mapping):
        return [int(puntajes[k]) for k in sorted(puntajes)]
    return [int(p) for p in puntajes]


def pd_completa(puntajes: Mapping[str, int] | Sequence[int]) -> int:
    return int(sum(_ordenar(puntajes)))


def pd_manual(puntajes: Mapping[str, int] | Sequence[int], n_fallos: int = N_FALLOS_PARADA) -> int:
    """PD con la regla de parada aplicada a posteriori (figuras en orden F01..F15)."""
    total, seguidos = 0, 0
    for p in _ordenar(puntajes):
        if seguidos >= n_fallos:
            break
        if p:
            total += 1
            seguidos = 0
        else:
            seguidos += 1
    return total
