"""Ensambla el vector de los 6 indicadores para una figura."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from grafomotor import ORDEN

__all__ = ["ORDEN", "VectorIndicadores", "extraer_indicadores"]


@dataclass
class VectorIndicadores:
    figura_id: str
    valores: dict[str, float]          # normalizados 0..1 (1 = como el modelo)
    raw: dict[str, float] = field(default_factory=dict)  # crudos, para el panel técnico

    def as_row(self) -> list[float]:
        return [self.valores[k] for k in ORDEN]


def extraer_indicadores(
    figura_bin: np.ndarray,
    plantilla_bin: np.ndarray,
    figura_id: str,
    meta_figura: dict,
) -> VectorIndicadores:
    """meta_figura: {'vertices_esperados': int, 'intersecciones_esperadas': int, ...}

    Importa `indicadores` de forma perezosa (usa OpenCV/scikit-image).
    """
    from grafomotor.features import indicadores as ind

    v_esp = int(meta_figura.get("vertices_esperados", 0))
    i_esp = int(meta_figura.get("intersecciones_esperadas", 0))

    pm_n, pm_r = ind.precision_modelo(figura_bin, plantilla_bin)
    ve_n, ve_r = ind.vertices(figura_bin, v_esp)
    ea_n, ea_r = ind.error_angular(figura_bin, plantilla_bin)
    ci_n, ci_r = ind.cierre(figura_bin)
    it_n, it_r = ind.intersecciones(figura_bin, plantilla_bin, i_esp)
    pr_n, pr_r = ind.proporcion(figura_bin, plantilla_bin)

    return VectorIndicadores(
        figura_id=figura_id,
        valores={
            "precision_modelo": pm_n, "vertices": ve_n, "error_angular": ea_n,
            "cierre": ci_n, "intersecciones": it_n, "proporcion": pr_n,
        },
        raw={
            "iou": pm_r, "n_vertices": ve_r, "error_angular_deg": ea_r,
            "extremos_libres": ci_r, "dist_interseccion_px": it_r, "razon_aspecto": pr_r,
        },
    )
