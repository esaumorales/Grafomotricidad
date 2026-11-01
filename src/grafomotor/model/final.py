"""Predicción con el modelo final del artículo (Random Forest con indicadores generales + por criterio del
manual, sin razón de proporción), usado por la aplicación web.

Entrada: la figura binaria ya procesada (trazo blanco, 512 px, alineada con la plantilla), la que deja
`grafomotor.preprocessing.preprocesar_figura` en `figura_bin`. Salida: probabilidad de que la figura sea
correcta, la nota (1/0) con el punto de corte del modelo y la decisión de la revisión por confianza:
nota automática si la probabilidad es <= límite inferior (incorrecta) o >= límite superior (correcta);
si no, "revisar" (la califica el docente).

La carpeta de una versión es autónoma: `modelo.joblib`, `manifiesto.json` y `plantillas/` (las plantillas
con que se midió el entrenamiento; el manifiesto guarda también sus medidas esperadas en `figuras_meta`).
La deja lista `scripts/instalar_modelo_final.py`.

    m = ModeloFinal("models/final/modelo_rf_103e_83")
    r = m.predecir_figura(figura_bin, "F05")      # {'prob': .., 'nota': .., 'decision': .., 'x': .., 'vec': ..}
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import joblib
import numpy as np

from grafomotor.features.criterios import _dif_angular, medir
from grafomotor.features.extract import VectorIndicadores, extraer_indicadores
from grafomotor.io import a_binaria, leer_gris

CR = ["partes", "partes_juntas", "dist_partes", "extremos", "cruces", "ondas", "esquinas", "giro_max",
      "incl_partes"]


def fila_entrada(binaria: np.ndarray, figura_id: str, plantilla: np.ndarray, figura_meta: dict,
                 ref: dict, nombres: list[str]) -> np.ndarray:
    """Vector de entrada en el orden de `nombres` (el del manifiesto), igual que en el entrenamiento."""
    return _fila(binaria, figura_id, plantilla, figura_meta, ref, nombres)[0]


def _fila(binaria, figura_id, plantilla, figura_meta, ref, nombres) -> tuple[np.ndarray, VectorIndicadores]:
    vec = extraer_indicadores(binaria, plantilla, figura_id, figura_meta)
    v = {**vec.valores, **{f"raw_{k}": x for k, x in vec.raw.items()}}
    cr = medir(binaria)
    for c in CR + ["angulo"]:
        a, b = cr.get(c, math.nan), ref[figura_id][c]
        if c != "angulo":
            v[f"cr_{c}"] = float(a)
        v[f"dif_{c}"] = _dif_angular(a, b) if c == "angulo" else abs(float(a) - float(b))
    for f in figura_meta.get("_todas", []):
        v[f"fig_{f}"] = 1.0 if f == figura_id else 0.0
    x = np.array([[float(v.get(n, math.nan)) for n in nombres]])
    x[np.isinf(x)] = np.nan
    return x, vec


class ModeloFinal:
    def __init__(self, carpeta: str | Path):
        self.carpeta = Path(carpeta)
        self.modelo = joblib.load(self.carpeta / "modelo.joblib")
        self.man = json.loads((self.carpeta / "manifiesto.json").read_text(encoding="utf-8"))
        self.version = self.man["version"]
        self.nombres = self.man["feature_names"]
        self.corte = self.man["punto_de_corte"]
        self.li = self.man["limites_confianza"]["incorrecta_si_prob_menor_o_igual"]
        self.ls = self.man["limites_confianza"]["correcta_si_prob_mayor_o_igual"]
        self.ref = self.man["criterios_plantilla"]
        # medidas esperadas de cada figura (vértices e intersecciones) de las plantillas del entrenamiento
        self.figuras_meta: dict[str, dict] = self.man.get("figuras_meta", {})
        self._plantillas: dict[str, np.ndarray] | None = None

    # --- plantillas propias del modelo -----------------------------------------------------------
    @property
    def dir_plantillas(self) -> Path:
        return self.carpeta / "plantillas"

    @property
    def plantillas(self) -> dict[str, np.ndarray]:
        if self._plantillas is None:
            self._plantillas = {f: a_binaria(leer_gris(self.dir_plantillas / f"{f}.png"))
                                for f in self.man["figuras"] if (self.dir_plantillas / f"{f}.png").exists()}
        return self._plantillas

    # --- predicción ----------------------------------------------------------------------------
    def _decidir(self, p: float) -> dict:
        decision = "incorrecta" if p <= self.li else "correcta" if p >= self.ls else "revisar"
        return {"prob": round(p, 4), "nota": int(p >= self.corte), "decision": decision}

    def probabilidad(self, binaria, figura_id, plantilla, figura_meta) -> float:
        meta = {**figura_meta, "_todas": self.man["figuras"]}
        return float(self.modelo.predict_proba(fila_entrada(binaria, figura_id, plantilla, meta, self.ref,
                                                            self.nombres))[0, 1])

    def predecir(self, binaria, figura_id, plantilla, figura_meta) -> dict:
        return self._decidir(self.probabilidad(binaria, figura_id, plantilla, figura_meta))

    def predecir_figura(self, binaria: np.ndarray, figura_id: str) -> dict:
        """Con las plantillas y medidas del propio modelo. Devuelve además `x` (fila de entrada, para SHAP)
        y `vec` (indicadores generales, para mostrarlos)."""
        meta = {**self.figuras_meta[figura_id], "_todas": self.man["figuras"]}
        x, vec = _fila(binaria, figura_id, self.plantillas[figura_id], meta, self.ref, self.nombres)
        return {**self._decidir(float(self.modelo.predict_proba(x)[0, 1])), "x": x[0], "vec": vec}
