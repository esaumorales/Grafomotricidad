"""
Test de contrato de inferencia.

Garantiza que el modelo servido en producción da EXACTAMENTE la misma salida
que la validada. Se rellena `CASOS_FIJOS` tras entrenar (script 03) con unos pocos
vectores de indicadores y su predicción esperada. Si algún día una versión de
librería cambia el resultado, este test lo detecta.
"""
import numpy as np
import pytest

from grafomotor.features.extract import ORDEN

# (vector en el orden de ORDEN)  ->  puntaje esperado (0/1)
# Generado con el modelo entrenado sobre datos SINTÉTICOS (scripts/03_entrenar.py).
# Al reentrenar con datos reales, regenerar con:
#   python -c "import pandas as pd,numpy as np,joblib; from grafomotor import ORDEN; \
#     m=joblib.load('models/actual/modelo_xgb.joblib'); df=pd.read_parquet('data/processed/features.parquet'); \
#     X=df[ORDEN].to_numpy(float); \
#     [print((list(np.round(X[i],4)), int(m.predict(X[i:i+1])[0]))) for i in [0,100,300,600,-1]]"
CASOS_FIJOS: list[tuple[list[float], int]] = [
    ([0.037974, 0.0, 0.003146, 0.0, 0.0, 0.988318], 0),        # prob 0.007
    ([0.034848, 0.0, 0.006534, 0.0, 0.0, 0.987616], 0),        # prob 0.007
    ([0.041323, 0.0, 0.981713, 0.0, 0.0, 0.725661], 0),        # prob 0.008
    ([0.0, 0.0, 0.986726, 1.0, 1.0, 1.0], 1),                  # prob 0.996
    ([0.392983, 0.666667, 0.992715, 0.0, 0.986979, 1.0], 1),   # prob 0.993
]


@pytest.mark.skipif(not CASOS_FIJOS, reason="rellenar CASOS_FIJOS tras entrenar el modelo")
def test_inferencia_estable():
    from grafomotor.model.registry import cargar_modelo
    from grafomotor.config import load_config

    modelo, _ = cargar_modelo(load_config().ruta("models") / "actual")
    for vec, esperado in CASOS_FIJOS:
        assert len(vec) == len(ORDEN)
        pred = int(modelo.predict(np.array([vec], dtype=float))[0])
        assert pred == esperado, f"vector {vec}: esperado {esperado}, obtuve {pred}"
