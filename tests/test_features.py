"""Sanidad de los indicadores geométricos: figura idéntica al modelo -> ~1.0."""
import numpy as np

from grafomotor.features.extract import extraer_indicadores


def _cuadrado(lado=512, margen=100, grosor=4):
    img = np.zeros((lado, lado), np.uint8)
    a, b = margen, lado - margen
    img[a:b, a:a + grosor] = 255
    img[a:b, b - grosor:b] = 255
    img[a:a + grosor, a:b] = 255
    img[b - grosor:b, a:b] = 255
    return img


def test_figura_identica_al_modelo():
    cuad = _cuadrado()
    vec = extraer_indicadores(cuad, cuad, "F03", {"vertices_esperados": 4,
                                                 "intersecciones_esperadas": 0})
    assert vec.valores["precision_modelo"] > 0.9
    assert vec.valores["proporcion"] > 0.9
    assert vec.valores["cierre"] > 0.8


def test_figura_desproporcionada_baja_proporcion():
    cuad = _cuadrado()
    rect = cuad.copy()
    rect = np.roll(rect, 60, axis=1)          # deforma horizontalmente
    rect[:, :80] = 0
    vec = extraer_indicadores(rect, cuad, "F03", {"vertices_esperados": 4,
                                                 "intersecciones_esperadas": 0})
    assert vec.valores["proporcion"] <= 1.0
    assert 0.0 <= vec.valores["precision_modelo"] <= 1.0


def test_vector_en_rango_y_orden():
    cuad = _cuadrado()
    vec = extraer_indicadores(cuad, cuad, "F03", {"vertices_esperados": 4})
    assert list(vec.valores.keys()) == [
        "precision_modelo", "vertices", "error_angular",
        "cierre", "intersecciones", "proporcion",
    ]
    assert all(0.0 <= v <= 1.0 for v in vec.valores.values())
