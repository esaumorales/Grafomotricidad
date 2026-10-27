"""Inferencia: del vector de indicadores a la puntuación por figura y a la sesión completa."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from grafomotor import ORDEN
from grafomotor.model.columnas import fila


@dataclass
class PrediccionFigura:
    figura_id: str
    puntaje: int          # 0/1
    prob: float           # probabilidad de "correcta"
    indicadores: dict[str, float]
    # revisión por confianza (modelo final): correcta | incorrecta | revisar; "" en los modelos antiguos
    decision: str = ""


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


def predecir_figura(modelo, vector: dict[str, float], figura_id: str,
                    crudos: dict[str, float] | None = None,
                    nombres: list[str] | None = None) -> PrediccionFigura:
    """nombres: columnas del modelo (manifiesto); por defecto, los 6 indicadores."""
    x = np.array([fila(vector, crudos or {}, figura_id, nombres or ORDEN)], dtype=float)
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
