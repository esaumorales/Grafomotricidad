"""Predicción con el modelo final del artículo (Random Forest con indicadores generales + por criterio del
manual, sin razón de proporción), para integrarlo en la aplicación web.

Entrada: la figura binaria ya procesada (trazo blanco, 512 px, alineada con la plantilla), la que deja
`grafomotor.preprocessing.preprocesar_figura` en `figura_bin`. Salida: probabilidad de que la figura sea
correcta, la nota (1/0) con el punto de corte del modelo y la decisión de la revisión por confianza:
nota automática si la probabilidad es <= límite inferior (incorrecta) o >= límite superior (correcta);
si no, "revisar" (la califica el docente).

    m = ModeloFinal("modelos/modelo_rf_103e_83")      # carpeta con modelo.joblib + manifiesto.json
    r = m.predecir(figura_bin, "F05")                 # {'prob': .., 'nota': .., 'decision': ..}
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import joblib
import numpy as np

from criterios import _dif_angular, medir
from grafomotor.features.extract import extraer_indicadores

CR = ["partes", "partes_juntas", "dist_partes", "extremos", "cruces", "ondas", "esquinas", "giro_max",
      "incl_partes"]


def fila_entrada(binaria: np.ndarray, figura_id: str, plantilla: np.ndarray, figura_meta: dict,
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
    def __init__(self, carpeta: str | Path):
        carpeta = Path(carpeta)
        self.modelo = joblib.load(carpeta / "modelo.joblib")
        self.man = json.loads((carpeta / "manifiesto.json").read_text(encoding="utf-8"))
        self.nombres = self.man["feature_names"]
        self.corte = self.man["punto_de_corte"]
        self.li, self.ls = self.man["limites_confianza"]["incorrecta_si_prob_menor_o_igual"], \
            self.man["limites_confianza"]["correcta_si_prob_mayor_o_igual"]
        self.ref = self.man["criterios_plantilla"]

    def probabilidad(self, binaria, figura_id, plantilla, figura_meta) -> float:
        meta = {**figura_meta, "_todas": self.man["figuras"]}
        return float(self.modelo.predict_proba(fila_entrada(binaria, figura_id, plantilla, meta, self.ref,
                                                            self.nombres))[0, 1])

    def predecir(self, binaria, figura_id, plantilla, figura_meta) -> dict:
        p = self.probabilidad(binaria, figura_id, plantilla, figura_meta)
        decision = "incorrecta" if p <= self.li else "correcta" if p >= self.ls else "revisar"
        return {"prob": round(p, 4), "nota": int(p >= self.corte), "decision": decision}
