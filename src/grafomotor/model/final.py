"""
Modelo final de la aplicación (Random Forest con indicadores generales + por criterio del
manual, sin razón de proporción). Carga el artefacto que guarda
`experimentos/articulo_103e/mejora/paso12_guardar_modelo.py` (carpeta con `modelo.joblib` +
`manifiesto.json`) y arma el vector de entrada igual que en el entrenamiento, para que la
probabilidad sea la misma que la del artículo.

Copia (adaptada a las rutas del paquete) de `experimentos/articulo_103e/prediccion_final.py`,
que queda congelado como código de referencia del experimento.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import joblib
import numpy as np

from grafomotor.features.criterios import _dif_angular, medir
from grafomotor.features.extract import extraer_indicadores

# criterios que se comparan contra la plantilla (ver features/criterios.py); "angulo" aparte
# porque la diferencia se calcula circular (0-180°), no como resta simple.
CR = ["partes", "partes_juntas", "dist_partes", "extremos", "cruces", "ondas", "esquinas",
      "giro_max", "incl_partes"]


def _fila_entrada(binaria: np.ndarray, figura_id: str, plantilla: np.ndarray, figura_meta: dict,
                  ref: dict, nombres: list[str]) -> np.ndarray:
    """Vector de entrada en el orden de `nombres` (el del manifiesto), igual que en el entrenamiento."""
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
    return x


class ModeloFinal:
    """carpeta: `modelo.joblib` + `manifiesto.json` (ver paso12_guardar_modelo.py)."""

    def __init__(self, carpeta: str | Path):
        carpeta = Path(carpeta)
        self.modelo = joblib.load(carpeta / "modelo.joblib")
        self.manifiesto = json.loads((carpeta / "manifiesto.json").read_text(encoding="utf-8"))
        self.nombres: list[str] = self.manifiesto["feature_names"]
        self.corte: float = self.manifiesto["punto_de_corte"]
        lim = self.manifiesto["limites_confianza"]
        self.li, self.ls = lim["incorrecta_si_prob_menor_o_igual"], lim["correcta_si_prob_mayor_o_igual"]
        self.ref: dict = self.manifiesto["criterios_plantilla"]
        self.figuras: list[str] = self.manifiesto["figuras"]

    def shap_entrada(self, X: np.ndarray) -> tuple[object, np.ndarray, list[str]]:
        """(estimador de árboles, X ya imputado, nombres de columna) para `shap.TreeExplainer`:
        el modelo guardado es un `Pipeline` (imputación + bosque) y SHAP necesita el árbol solo,
        con los datos ya pasados por la imputación (si el imputador agrega columnas de
        'faltaba este dato', se nombran aparte para que sigan sumando al indicador correcto)."""
        pasos = getattr(self.modelo, "named_steps", None)
        if not pasos:
            return self.modelo, X, self.nombres
        *previos, (_, estimador) = pasos.items()
        nombres = list(self.nombres)
        for _, paso in previos:
            X = paso.transform(X)
            indicador = getattr(paso, "indicator_", None)
            if indicador is not None:
                nombres += [f"falta_{self.nombres[i]}" for i in indicador.features_]
        return estimador, X, nombres

    def fila(self, binaria: np.ndarray, figura_id: str, plantilla: np.ndarray,
            figura_meta: dict) -> np.ndarray:
        """Vector de entrada de una figura, en el orden de `self.nombres` (para SHAP)."""
        meta = {**figura_meta, "_todas": self.figuras}
        return _fila_entrada(binaria, figura_id, plantilla, meta, self.ref, self.nombres)

    def predecir(self, binaria: np.ndarray, figura_id: str, plantilla: np.ndarray,
                figura_meta: dict, sin_trazo: bool = False) -> dict:
        """{'prob', 'nota', 'decision'}. `decision`: 'correcta'/'incorrecta' (nota automática),
        'revisar' (la confirma el docente) o 'sin trazo' (el niño no copió la figura; nota 0
        sin consultar al modelo, como en el CUMANIN)."""
        if sin_trazo:
            return {"prob": 0.0, "nota": 0, "decision": "sin trazo"}
        prob = float(self.modelo.predict_proba(self.fila(binaria, figura_id, plantilla, figura_meta))[0, 1])
        decision = "incorrecta" if prob <= self.li else "correcta" if prob >= self.ls else "revisar"
        return {"prob": round(prob, 4), "nota": int(prob >= self.corte), "decision": decision}
