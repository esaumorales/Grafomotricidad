"""Atajo: los indicadores por criterio del manual viven ahora en `grafomotor.features.criterios`.
Se conserva este módulo para que los scripts del experimento sigan importando `from criterios import ...`."""
from grafomotor.features.criterios import *  # noqa: F401,F403
from grafomotor.features.criterios import (  # noqa: F401
    CIERRE_PX,
    HUECO_MIN_PX,
    SUAVE_SIGMA,
    _dif_angular,
    _podar,
    _vecinos,
    medir,
)
