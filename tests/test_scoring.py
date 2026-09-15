from grafomotor.scoring.baremo import tramo_de_edad
from grafomotor.scoring.niveles import nivel_desde_T


def test_tramos_tabla_b9():
    """Tramos reales de la Tabla B.9 (CUMANIN, pág. 83): no son de ancho uniforme."""
    assert tramo_de_edad(36) == "36_42"
    assert tramo_de_edad(42) == "36_42"
    assert tramo_de_edad(43) == "43_48"
    assert tramo_de_edad(60) == "55_60"
    assert tramo_de_edad(71) == "67_78"


def test_tramo_fuera_de_rango():
    import pytest
    with pytest.raises(ValueError):
        tramo_de_edad(72)   # 6;0 queda fuera del estudio (3-5)


def test_cortes_cumanin_2_clases():
    assert nivel_desde_T(45, n_clases=2).nivel == "Adecuado"
    assert nivel_desde_T(45, n_clases=2).accion == "ninguna"
    assert nivel_desde_T(40, n_clases=2).nivel == "En riesgo"
    assert nivel_desde_T(40, n_clases=2).accion == "reforzar_y_revaluar"
    assert nivel_desde_T(30, n_clases=2).nivel == "En riesgo"
    assert nivel_desde_T(30, n_clases=2).accion == "derivar"


def test_cortes_cumanin_3_clases():
    assert nivel_desde_T(55, n_clases=3).nivel == "Adecuado"
    assert nivel_desde_T(35, n_clases=3).nivel == "Bajo"
    assert nivel_desde_T(28, n_clases=3).nivel == "Muy bajo"


def test_descriptor_verbal_tabla_5_2():
    assert nivel_desde_T(72).descriptor_verbal == "Muy alto"
    assert nivel_desde_T(50).descriptor_verbal == "Medio"
    assert nivel_desde_T(25).descriptor_verbal == "Muy bajo"
