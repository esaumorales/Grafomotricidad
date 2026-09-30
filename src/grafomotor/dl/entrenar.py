"""
Entrenamiento del modelo B en dos fases.

  Fase 1: la red preentrenada queda CONGELADA (y sus BatchNorm en modo evaluación);
          solo se entrenan las 15 cabezas.
  Fase 2: se descongelan las últimas capas y se ajustan con una tasa baja.

Desbalance: pérdida BCE con pesos por clase calculados POR FIGURA en el
entrenamiento (efecto suelo a los 3 años, figuras fáciles casi siempre correctas).

Parada temprana: se reserva un 15 % de los NIÑOS del entrenamiento como validación
interna (nunca se mira el fold de prueba) y se guarda el mejor estado.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

import cv2
import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import GroupShuffleSplit
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision.transforms import functional as TF

from grafomotor.dl.aumentos import (
    DE_IMAGENET,
    MEDIA_IMAGENET,
    transformacion_entrenamiento,
    transformacion_evaluacion,
)
from grafomotor.dl.modelo import RedMultiCabeza
from grafomotor.dl.utilidades import dispositivo as elegir_dispositivo
from grafomotor.dl.utilidades import fijar_semilla
from grafomotor.logs import obtener_logger

log = obtener_logger(__name__)

CONFIG_POR_DEFECTO = {
    "arquitectura": "resnet18",
    "aumento": "moderado",           # moderado | robusto (ver dl/aumentos.py)
    "tta": False,                    # TTA solo como variante (ensamblar-dl)
    "lote": 64,
    "epocas_fase1": 8,
    "epocas_fase2": 15,
    "lr_fase1": 1e-3,
    "lr_fase2_red": 1e-4,
    "lr_fase2_cabezas": 3e-4,
    "peso_decaimiento": 1e-4,
    "paciencia": 5,
    "fraccion_validacion": 0.15,
    "semilla": 20260930,
    "trabajadores": 0,
}


class DatasetFiguras(Dataset):
    """Imágenes 224×224 en gris ya preparadas (dl/imagen.py), cargadas en memoria."""

    def __init__(self, df: pd.DataFrame, carpeta, figuras: list[str], transform):
        self.idx_fig = {f: i for i, f in enumerate(figuras)}
        self.imgs = [cv2.imread(str(carpeta / r), cv2.IMREAD_GRAYSCALE) for r in df["dl_path"]]
        self.fig = df["figura_id"].map(self.idx_fig).to_numpy()
        self.y = (df["puntaje"].to_numpy(np.float32) if "puntaje" in df
                  else np.zeros(len(df), np.float32))
        self.transform = transform

    def __len__(self) -> int:
        return len(self.imgs)

    def __getitem__(self, i):
        return self.transform(self.imgs[i]), int(self.fig[i]), self.y[i]


def pesos_por_figura(df: pd.DataFrame, figuras: list[str]) -> torch.Tensor:
    """(15, 2): peso de la clase 0 y de la clase 1 para cada figura (balanceado)."""
    w = torch.ones(len(figuras), 2)
    for i, f in enumerate(figuras):
        y = df.loc[df["figura_id"] == f, "puntaje"]
        if len(y) == 0:
            continue
        p1 = float(np.clip(y.mean(), 0.05, 0.95))
        w[i, 0], w[i, 1] = 0.5 / (1 - p1), 0.5 / p1
    return w


@dataclass
class ResultadoFold:
    modelo: RedMultiCabeza
    historial: list[dict] = field(default_factory=list)
    mejor_epoca: int = -1


def _perdida(logits, y, fig, pesos):
    w = pesos[fig, y.long()]
    return (nn.functional.binary_cross_entropy_with_logits(logits, y, reduction="none") * w).mean()


def _una_epoca(modelo, cargador, pesos, disp, optim=None, escalador=None) -> float:
    entrenando = optim is not None
    total, n = 0.0, 0
    with torch.set_grad_enabled(entrenando):
        for x, fig, y in cargador:
            x, fig, y = x.to(disp), fig.to(disp), y.to(disp)
            with torch.autocast(device_type=disp.type, enabled=disp.type == "cuda"):
                logits = modelo(x, fig)
            loss = _perdida(logits.float(), y, fig, pesos)
            if entrenando:
                optim.zero_grad(set_to_none=True)
                escalador.scale(loss).backward()
                escalador.step(optim)
                escalador.update()
            total += float(loss.detach()) * len(y)
            n += len(y)
    return total / max(n, 1)


def entrenar_fold(df_train: pd.DataFrame, carpeta, figuras: list[str], cfg: dict | None = None,
                  dispositivo: str | None = None, verbose: bool = True) -> ResultadoFold:
    cfg = {**CONFIG_POR_DEFECTO, **(cfg or {})}
    fijar_semilla(int(cfg["semilla"]))
    disp = elegir_dispositivo(dispositivo)

    # validación interna por niño
    gss = GroupShuffleSplit(n_splits=1, test_size=cfg["fraccion_validacion"],
                            random_state=cfg["semilla"])
    tr_idx, va_idx = next(gss.split(df_train, groups=df_train["child_id"]))
    d_tr, d_va = df_train.iloc[tr_idx], df_train.iloc[va_idx]

    kw = {"batch_size": cfg["lote"], "num_workers": cfg["trabajadores"],
          "pin_memory": disp.type == "cuda"}
    carg_tr = DataLoader(DatasetFiguras(d_tr, carpeta, figuras,
                                        transformacion_entrenamiento(cfg["aumento"])),
                         shuffle=True, drop_last=len(d_tr) > cfg["lote"], **kw)
    carg_va = DataLoader(DatasetFiguras(d_va, carpeta, figuras, transformacion_evaluacion()),
                         shuffle=False, **kw)
    pesos = pesos_por_figura(d_tr, figuras).to(disp)

    modelo = RedMultiCabeza(cfg["arquitectura"], len(figuras), preentrenada=True).to(disp)
    escalador = torch.amp.GradScaler(enabled=disp.type == "cuda")
    historial, mejor, mejor_estado, mejor_ep, sin_mejora = [], np.inf, None, -1, 0

    fases = [
        ("fase1", cfg["epocas_fase1"]),
        ("fase2", cfg["epocas_fase2"]),
    ]
    ep_global = 0
    for fase, n_ep in fases:
        if fase == "fase1":
            modelo.congelar_red()
            optim = torch.optim.AdamW(modelo.cabezas.parameters(), lr=cfg["lr_fase1"],
                                      weight_decay=cfg["peso_decaimiento"])
        else:
            ult = modelo.descongelar_ultimas_capas()
            optim = torch.optim.AdamW([
                {"params": ult, "lr": cfg["lr_fase2_red"]},
                {"params": modelo.cabezas.parameters(), "lr": cfg["lr_fase2_cabezas"]},
            ], weight_decay=cfg["peso_decaimiento"])
            sin_mejora = 0
        sched = torch.optim.lr_scheduler.CosineAnnealingLR(optim, T_max=max(n_ep, 1))

        for _ in range(n_ep):
            modelo.train()
            if fase == "fase1":
                modelo.red.eval()          # BatchNorm congelado
            l_tr = _una_epoca(modelo, carg_tr, pesos, disp, optim, escalador)
            modelo.eval()
            l_va = _una_epoca(modelo, carg_va, pesos, disp)
            sched.step()
            historial.append({"epoca": ep_global, "fase": fase, "perdida_train": round(l_tr, 4),
                              "perdida_val": round(l_va, 4)})
            if verbose:
                log.info("[%s] época %02d · pérdida train %.4f · val %.4f",
                         fase, ep_global, l_tr, l_va)
            if l_va < mejor - 1e-4:
                mejor, mejor_ep, sin_mejora = l_va, ep_global, 0
                mejor_estado = copy.deepcopy(modelo.state_dict())
            else:
                sin_mejora += 1
            ep_global += 1
            if fase == "fase2" and sin_mejora >= cfg["paciencia"]:
                break

    if mejor_estado is not None:
        modelo.load_state_dict(mejor_estado)
    modelo.eval()
    return ResultadoFold(modelo=modelo, historial=historial, mejor_epoca=mejor_ep)


# Aumento en la prueba (TTA), como Langer et al. (2024): rotaciones pequeñas y deterministas.
# Se promedian las probabilidades; ±2° no cambia ningún criterio del CUMANIN.
ANGULOS_TTA = (-2.0, 0.0, 2.0)
_BLANCO_NORMALIZADO = [(1 - m) / d for m, d in zip(MEDIA_IMAGENET, DE_IMAGENET, strict=True)]


def _probabilidades(modelo: RedMultiCabeza, x: torch.Tensor, fig: torch.Tensor,
                    angulos: tuple[float, ...]) -> np.ndarray:
    """Media de sigmoid(logit) sobre las rotaciones de `angulos` (x ya normalizado)."""
    total = torch.zeros(x.shape[0], device=x.device)
    for ang in angulos:
        xi = x if ang == 0 else TF.rotate(x, ang, fill=_BLANCO_NORMALIZADO)
        with torch.autocast(device_type=x.device.type, enabled=x.device.type == "cuda"):
            total += torch.sigmoid(modelo(xi, fig).float())
    return (total / len(angulos)).cpu().numpy()


@torch.no_grad()
def predecir(modelo: RedMultiCabeza, df: pd.DataFrame, carpeta, figuras: list[str],
             dispositivo: str | None = None, lote: int = 128, tta: bool = False) -> np.ndarray:
    """Probabilidad de 'figura correcta' para cada fila de df (con TTA si se pide)."""
    disp = torch.device(dispositivo or next(modelo.parameters()).device)
    ds = DatasetFiguras(df, carpeta, figuras, transformacion_evaluacion())
    angulos = ANGULOS_TTA if tta else (0.0,)
    modelo.eval()
    probs = [_probabilidades(modelo, x.to(disp), fig.to(disp), angulos)
             for x, fig, _ in DataLoader(ds, batch_size=lote, shuffle=False)]
    return np.concatenate(probs) if probs else np.zeros(0)


@torch.no_grad()
def predecir_arrays(modelo: RedMultiCabeza, imgs: list[np.ndarray], fig_idx: list[int],
                    lote: int = 128, tta: bool = False) -> np.ndarray:
    """Igual que `predecir` pero sobre imágenes ya preparadas en memoria (robustez)."""
    disp = next(modelo.parameters()).device
    tf = transformacion_evaluacion()
    angulos = ANGULOS_TTA if tta else (0.0,)
    modelo.eval()
    out = []
    for i in range(0, len(imgs), lote):
        x = torch.stack([tf(im) for im in imgs[i:i + lote]]).to(disp)
        f = torch.tensor(fig_idx[i:i + lote], dtype=torch.long, device=disp)
        out.append(_probabilidades(modelo, x, f, angulos))
    return np.concatenate(out) if out else np.zeros(0)
