"""
Red común + 15 cabezas (una por figura), al estilo de Langer et al. (2024).

La columna vertebral (ResNet-18 o EfficientNet-B0, preentrenadas en ImageNet vía
`timm`) extrae un vector por imagen. Cada figura tiene su propia cabeza lineal
(logit de "figura correcta"); se implementan como una sola capa Linear de 15
salidas de la que se toma la columna de la figura: es equivalente a 15 cabezas
independientes (cada columna tiene sus propios pesos y solo recibe gradiente de
las imágenes de su figura).
"""
from __future__ import annotations

import timm
import torch
from torch import nn

ARQUITECTURAS = {"resnet18": "resnet18", "efficientnet_b0": "efficientnet_b0"}


class RedMultiCabeza(nn.Module):
    def __init__(self, arquitectura: str = "resnet18", n_figuras: int = 15,
                 preentrenada: bool = True, dropout: float = 0.2):
        super().__init__()
        if arquitectura not in ARQUITECTURAS:
            raise ValueError(
                f"arquitectura no soportada: {arquitectura} (usa {list(ARQUITECTURAS)})")
        self.arquitectura = arquitectura
        self.n_figuras = n_figuras
        self.red = timm.create_model(ARQUITECTURAS[arquitectura], pretrained=preentrenada,
                                     num_classes=0)
        self.dropout = nn.Dropout(dropout)
        self.cabezas = nn.Linear(self.red.num_features, n_figuras)

    def forward(self, x: torch.Tensor, figura_idx: torch.Tensor) -> torch.Tensor:
        """x: (B, 3, 224, 224) · figura_idx: (B,) enteros 0..14 -> logits (B,)."""
        z = self.dropout(self.red(x))
        return self.cabezas(z).gather(1, figura_idx.view(-1, 1)).squeeze(1)

    # --- fases de entrenamiento -------------------------------------------------
    def congelar_red(self) -> None:
        for p in self.red.parameters():
            p.requires_grad = False

    def descongelar_ultimas_capas(self) -> list[nn.Parameter]:
        """Descongela el último bloque de la red y devuelve sus parámetros."""
        if self.arquitectura == "resnet18":
            modulos = [self.red.layer4]
        else:
            modulos = [self.red.blocks[-2:], self.red.conv_head, self.red.bn2]
        params = []
        for m in modulos:
            for p in m.parameters():
                p.requires_grad = True
                params.append(p)
        return params

    def capa_objetivo_gradcam(self) -> nn.Module:
        return self.red.layer4[-1] if self.arquitectura == "resnet18" else self.red.blocks[-1]


class SalidaDeFigura(nn.Module):
    """Envoltura para Grad-CAM: fija la figura y devuelve (B, 1)."""

    def __init__(self, modelo: RedMultiCabeza, figura_idx: int):
        super().__init__()
        self.modelo, self.figura_idx = modelo, figura_idx

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        idx = torch.full((x.shape[0],), self.figura_idx, dtype=torch.long, device=x.device)
        return self.modelo(x, idx).unsqueeze(1)


def guardar(modelo: RedMultiCabeza, ruta, extra: dict | None = None) -> None:
    torch.save({"arquitectura": modelo.arquitectura, "n_figuras": modelo.n_figuras,
                "estado": modelo.state_dict(), **(extra or {})}, ruta)


def cargar(ruta, dispositivo: str = "cpu") -> tuple[RedMultiCabeza, dict]:
    d = torch.load(ruta, map_location=dispositivo, weights_only=False)
    m = RedMultiCabeza(d["arquitectura"], d["n_figuras"], preentrenada=False)
    m.load_state_dict(d["estado"])
    return m.to(dispositivo).eval(), d
