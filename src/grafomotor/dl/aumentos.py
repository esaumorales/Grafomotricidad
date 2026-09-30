"""
Aumento de datos MODERADO para el modelo B.

Permitido: brillo, contraste, sombra, desenfoque leve, perspectiva leve y rotación
de ±7° (dentro del rango de 5° a 10° acordado).

PROHIBIDO: volteos (horizontal/vertical) y rotaciones grandes. Cambian lo que se
califica: orientación de la figura, ángulos, "parado en la punta" (rombo vs. cuadrado).
`verificar_sin_volteos()` lo comprueba y los tests lo exigen.
"""
from __future__ import annotations

import numpy as np
import torch
from torchvision import transforms as T

MEDIA_IMAGENET = (0.485, 0.456, 0.406)
DE_IMAGENET = (0.229, 0.224, 0.225)
ROTACION_MAX_GRADOS = 7


class SombraAleatoria:
    """Oscurece un semiplano con borde difuso (sombra de la mano o del celular)."""

    def __init__(self, p: float = 0.3, fuerza: tuple[float, float] = (0.15, 0.4)):
        self.p, self.fuerza = p, fuerza

    def __call__(self, x: torch.Tensor) -> torch.Tensor:
        if torch.rand(1).item() >= self.p:
            return x
        _, h, w = x.shape
        ang = float(torch.rand(1)) * np.pi
        yy, xx = torch.meshgrid(torch.arange(h), torch.arange(w), indexing="ij")
        d = (xx - w / 2) * np.cos(ang) + (yy - h / 2) * np.sin(ang)
        mascara = torch.sigmoid(d / (0.06 * max(h, w)))
        f = self.fuerza[0] + float(torch.rand(1)) * (self.fuerza[1] - self.fuerza[0])
        return x * (1 - f * mascara)


def _tres_canales():
    # la red preentrenada espera 3 canales: se copia el canal gris
    return T.Lambda(lambda t: t.expand(3, -1, -1).clone())


PERFILES = ("moderado", "robusto")


def transformacion_entrenamiento(perfil: str = "moderado") -> T.Compose:
    """
    moderado: la versión inicial.
    robusto:  mismas familias de transformación, más intensas y frecuentes (sombra,
              desenfoque, luz) + pequeño desplazamiento y escala uniforme (el tamaño no
              se penaliza en el CUMANIN). Sigue sin volteos y con rotación ±7°.

    Ojo al reportar: la prueba de robustez sintética usa las mismas familias
    (sombra, desenfoque, brillo), así que B "robusto" parte con ventaja en esa
    prueba. La evidencia limpia es la doble foto de aula.
    """
    if perfil not in PERFILES:
        raise ValueError(f"perfil de aumento desconocido: {perfil} (usa {PERFILES})")
    r = perfil == "robusto"
    # ToTensor primero: las transformaciones geométricas trabajan sobre el tensor (fondo = 1.0)
    geometricas = [
        T.RandomApply([T.RandomRotation(ROTACION_MAX_GRADOS, fill=1.0)], p=0.5),
        T.RandomPerspective(distortion_scale=0.08, p=0.3, fill=1.0),
    ]
    if r:
        geometricas.append(T.RandomApply(
            [T.RandomAffine(degrees=0, translate=(0.05, 0.05), scale=(0.9, 1.1), fill=1.0)],
            p=0.5))
    return T.Compose([
        T.ToTensor(),
        *geometricas,
        _tres_canales(),
        T.ColorJitter(brightness=0.45 if r else 0.3, contrast=0.5 if r else 0.3),
        SombraAleatoria(p=0.5, fuerza=(0.15, 0.6)) if r else SombraAleatoria(p=0.3),
        T.RandomApply([T.GaussianBlur(kernel_size=9 if r else 5,
                                      sigma=(0.1, 2.0) if r else (0.1, 1.2))],
                      p=0.45 if r else 0.3),
        T.Normalize(MEDIA_IMAGENET, DE_IMAGENET),
    ])


def transformacion_evaluacion() -> T.Compose:
    return T.Compose([T.ToTensor(), _tres_canales(), T.Normalize(MEDIA_IMAGENET, DE_IMAGENET)])


def verificar_sin_volteos(tf: T.Compose) -> None:
    """Falla si la cadena incluye volteos o rotaciones fuera del rango permitido."""
    def _recorrer(t):
        if isinstance(t, (T.Compose, T.RandomApply)):
            for s in t.transforms:
                _recorrer(s)
        elif isinstance(t, (T.RandomHorizontalFlip, T.RandomVerticalFlip)):
            raise AssertionError(f"volteo prohibido: {t}")
        elif isinstance(t, T.RandomRotation) and max(abs(d) for d in t.degrees) > 10:
            raise AssertionError(f"rotación demasiado grande: {t.degrees}")
    _recorrer(tf)
