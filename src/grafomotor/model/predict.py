"""Inferencia: del vector de indicadores a la puntuación por figura y a la sesión completa."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from grafomotor import ORDEN


@dataclass
class PrediccionFigura:
    figura_id: str
    puntaje: int          # 0/1
    prob: float           # probabilidad de "correcta"
    indicadores: dict[str, float]


@dataclass
class PrediccionSesion:
    child_id: str
    edad_meses: int
    figuras: list[PrediccionFigura]
    PD: int               # suma de puntajes
    confianza_media: float

    @property
    def n_figuras(self) -> int:
        return len(self.figuras)


def predecir_figura(modelo, vector: dict[str, float], figura_id: str) -> PrediccionFigura:
    x = np.array([[vector[k] for k in ORDEN]], dtype=float)
    prob = float(modelo.predict_proba(x)[0, 1])
    return PrediccionFigura(
        figura_id=figura_id,
        puntaje=int(prob >= 0.5),
        prob=round(prob, 3),
        indicadores={k: round(float(vector[k]), 3) for k in ORDEN},
    )


def agregar_sesion(child_id: str, edad_meses: int,
                   preds: list[PrediccionFigura]) -> PrediccionSesion:
    conf = np.mean([abs(p.prob - 0.5) * 2 for p in preds]) if preds else 0.0
    return PrediccionSesion(
        child_id=child_id,
        edad_meses=edad_meses,
        figuras=preds,
        PD=int(sum(p.puntaje for p in preds)),
        confianza_media=round(float(conf), 3),
    )
