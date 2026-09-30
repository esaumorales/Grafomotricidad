"""Utilidades comunes del modelo B: dispositivo de cómputo y reproducibilidad."""
from __future__ import annotations

import random

import numpy as np
import torch


def dispositivo(preferido: str | None = None) -> torch.device:
    """GPU si hay CUDA (o el dispositivo pedido explícitamente), si no CPU."""
    if preferido:
        return torch.device(preferido)
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def fijar_semilla(semilla: int) -> None:
    """Fija el azar de Python, NumPy y PyTorch (inicialización, orden de lotes, aumentos).

    No fuerza algoritmos deterministas de cuDNN (serían más lentos); por eso dos corridas
    con la misma semilla en GPU pueden diferir en el tercer decimal. La variabilidad que
    se reporta en el artículo es la ENTRE semillas (`--semillas N`).
    """
    random.seed(semilla)
    np.random.seed(semilla)
    torch.manual_seed(semilla)
    torch.cuda.manual_seed_all(semilla)
