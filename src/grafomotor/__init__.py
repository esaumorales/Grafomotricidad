"""Evaluación grafomotora infantil por visión computacional + XGBoost + explicación para docentes."""

__version__ = "0.1.0"

# Los 6 indicadores geométricos (Tabla 1 del PPI) y su nombre para el docente.
INDICADORES = {
    "precision_modelo": "Parecido general con el modelo",
    "vertices": "Esquinas de la figura",
    "error_angular": "Inclinación de los ángulos",
    "cierre": "Cierre de las figuras",
    "intersecciones": "Cruce de líneas",
    "proporcion": "Tamaño de las partes",
}

# Orden canónico del vector de entrada del modelo. Definido aquí (sin dependencias
# pesadas) para que `model.predict` no tenga que importar OpenCV/scikit-image.
ORDEN = list(INDICADORES.keys())
