"""
Los dos modelos, de la FOTO (en memoria, escala de grises) a la probabilidad de
"figura correcta". Misma interfaz para A y B, para que la robustez y la practicidad
los traten igual.

Cada predictor guarda un modelo por *clave*: el número de fold (evaluación sin fuga:
cada niño se predice con el modelo que no lo vio) o "final" (uso en producción).
"""
from __future__ import annotations

from collections.abc import Hashable, Mapping, Sequence

import numpy as np
import pandas as pd

from grafomotor import ORDEN
from grafomotor.artefactos import Artefactos
from grafomotor.config import Config
from grafomotor.evaluation.particiones import folds_de
from grafomotor.features.extract import extraer_indicadores
from grafomotor.io import cargar_plantillas
from grafomotor.logs import obtener_logger
from grafomotor.model.dataset import Datos, construir
from grafomotor.model.registry import cargar_modelo
from grafomotor.model.train import ajustar_por_fold
from grafomotor.preprocessing import preprocesar_gris

log = obtener_logger(__name__)


def modelos_ml_por_fold(cfg: Config, etiquetas: pd.DataFrame, particiones: pd.DataFrame
                        ) -> tuple[dict[int, object], Datos]:
    """Un XGBoost por fold con los hiperparámetros del modelo A final, y los datos."""
    art = Artefactos.de_config(cfg)
    datos = construir(pd.read_parquet(art.features), etiquetas)
    base, _ = cargar_modelo(art.dir_modelo_ml)
    modelos = ajustar_por_fold(datos, folds_de(datos.grupos, particiones), base.get_params(),
                               cfg.get("modelo", "class_weight") == "balanced")
    return modelos, datos


class PredictorA:
    """Visión clásica + 6 indicadores + XGBoost."""

    nombre = "A"

    def __init__(self, cfg: Config, modelos: Mapping[Hashable, object]):
        self.modelos = dict(modelos)
        self.plantillas = cargar_plantillas(cfg)
        self.meta = cfg.figuras
        self.pre_cfg = cfg.get("preprocesamiento", default={})

    def predecir(self, gris: np.ndarray, figura_id: str, clave: Hashable) -> float:
        """Probabilidad; NaN si la foto no se pudo medir (cuenta como fallo)."""
        plantilla = self.plantillas[figura_id]
        try:
            res = preprocesar_gris(gris, plantilla, self.pre_cfg)
            vec = extraer_indicadores(res.figura_bin, plantilla, figura_id,
                                      self.meta.get(figura_id, {}))
        except Exception as e:
            log.debug("modelo A no pudo medir %s: %s", figura_id, e)
            return float("nan")
        x = np.array([[vec.valores[k] for k in ORDEN]])
        return float(self.modelos[clave].predict_proba(x)[0, 1])

    def predecir_lote(self, grises: Sequence[np.ndarray], figuras: Sequence[str],
                      clave: Hashable) -> np.ndarray:
        return np.array([self.predecir(g, f, clave) for g, f in zip(grises, figuras, strict=True)])


class PredictorB:
    """Preprocesamiento mínimo + red profunda (una pasada por lote en GPU)."""

    nombre = "B"

    def __init__(self, cfg: Config, modelos: Mapping[Hashable, object]):
        self.modelos = dict(modelos)
        self.idx = {f: i for i, f in enumerate(cfg.figuras)}
        self.lado = int(cfg.get("dl", "lado_px", default=224))

    @classmethod
    def desde_variante(cls, cfg: Config, variante: str, claves: str = "folds") -> PredictorB:
        """claves="folds": fold<k>.pt · claves="final": final.pt (o fold0.pt si no existe)."""
        from grafomotor.dl.modelo import cargar
        from grafomotor.dl.utilidades import dispositivo

        art, disp = Artefactos.de_config(cfg), dispositivo()
        carpeta = art.dir_modelo_dl(variante)
        if claves == "folds":
            rutas = {int(p.stem.removeprefix("fold")): p for p in carpeta.glob("fold*.pt")}
        else:
            final = art.modelo_dl_final(variante)
            rutas = {"final": final if final.exists() else art.modelo_dl_fold(variante, 0)}
        if not rutas:
            raise FileNotFoundError(f"no hay modelos entrenados en {carpeta}")
        return cls(cfg, {k: cargar(r, str(disp))[0] for k, r in rutas.items()})

    def predecir_lote(self, grises: Sequence[np.ndarray], figuras: Sequence[str],
                      clave: Hashable) -> np.ndarray:
        from grafomotor.dl.entrenar import predecir_arrays
        from grafomotor.dl.imagen import preparar_gris

        imgs = [preparar_gris(g, self.lado)[0] for g in grises]
        return predecir_arrays(self.modelos[clave], imgs, [self.idx[f] for f in figuras])
