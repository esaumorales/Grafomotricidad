"""
Grad-CAM (Selvaraju et al., 2017) para el modelo B.

Dos usos:
  1. Explicar DÓNDE miró la red para puntuar una figura (mapa de calor sobre la foto).
  2. Control de calidad: medir qué parte de la "atención" cae sobre el trazo del niño
     y qué parte cae en el borde de la imagen (sombras, borde de la hoja). Si la red
     mira sobre todo fuera del trazo, está aprendiendo un atajo.
"""
from __future__ import annotations

import cv2
import numpy as np
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.model_targets import BinaryClassifierOutputTarget

from grafomotor.dl.aumentos import transformacion_evaluacion
from grafomotor.dl.imagen import mascara_trazo
from grafomotor.dl.modelo import RedMultiCabeza, SalidaDeFigura


def mapa_gradcam(modelo: RedMultiCabeza, img224: np.ndarray, figura_idx: int,
                 clase: int = 1) -> np.ndarray:
    """Mapa 224×224 en [0, 1]. clase=1: qué hizo pensar 'correcta'; 0: 'incorrecta'."""
    disp = next(modelo.parameters()).device
    x = transformacion_evaluacion()(img224).unsqueeze(0).to(disp)
    envoltura = SalidaDeFigura(modelo, figura_idx).eval()
    with GradCAM(model=envoltura, target_layers=[modelo.capa_objetivo_gradcam()]) as cam:
        m = cam(input_tensor=x, targets=[BinaryClassifierOutputTarget(clase)])[0]
    return m.astype(np.float32)


def atencion_en_trazo(cam: np.ndarray, img224: np.ndarray, borde_frac: float = 0.08) -> dict:
    """Fracción de la masa de Grad-CAM sobre el trazo (dilatado) y en el borde de la imagen."""
    total = float(cam.sum()) or 1.0
    trazo = mascara_trazo(img224)
    h, w = cam.shape
    b = int(borde_frac * max(h, w))
    borde = np.zeros_like(trazo)
    borde[:b], borde[-b:], borde[:, :b], borde[:, -b:] = True, True, True, True
    return {
        "frac_en_trazo": round(float(cam[trazo].sum() / total), 3),
        "frac_area_trazo": round(float(trazo.mean()), 3),   # lo esperable por azar
        "frac_en_borde": round(float(cam[borde & ~trazo].sum() / total), 3),
    }


def superponer(img224: np.ndarray, cam: np.ndarray, alfa: float = 0.45) -> np.ndarray:
    """Imagen BGR con el mapa de calor encima (para figuras del artículo / panel técnico)."""
    color = cv2.applyColorMap((cam * 255).astype(np.uint8), cv2.COLORMAP_JET)
    base = cv2.cvtColor(img224, cv2.COLOR_GRAY2BGR)
    return cv2.addWeighted(color, alfa, base, 1 - alfa, 0)


__all__ = ["atencion_en_trazo", "mapa_gradcam", "superponer"]
