from grafomotor.scoring.baremo import tramo_de_edad
from grafomotor.scoring.niveles import nivel_desde_percentil, nivel_desde_T


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


def test_cortes_percentil_2_clases():
    assert nivel_desde_percentil(50, n_clases=2).nivel == "Adecuado"
    assert nivel_desde_percentil(50, n_clases=2).accion == "ninguna"
    assert nivel_desde_percentil(16, n_clases=2).nivel == "En riesgo"
    assert nivel_desde_percentil(16, n_clases=2).accion == "reforzar_y_revaluar"
    assert nivel_desde_percentil(2, n_clases=2).nivel == "En riesgo"
    assert nivel_desde_percentil(2, n_clases=2).accion == "derivar"


def test_cortes_percentil_3_clases():
    assert nivel_desde_percentil(50, n_clases=3).nivel == "Adecuado"
    assert nivel_desde_percentil(10, n_clases=3).nivel == "Bajo"
    assert nivel_desde_percentil(1, n_clases=3).nivel == "Muy bajo"


def test_descriptor_verbal_bandas_estandar():
    assert nivel_desde_percentil(99).descriptor_verbal == "Muy alto"
    assert nivel_desde_percentil(50).descriptor_verbal == "Medio"
    assert nivel_desde_percentil(1).descriptor_verbal == "Muy bajo"


def test_descriptor_verbal_tabla_5_2_historica():
    assert nivel_desde_T(72).descriptor_verbal == "Muy alto"
    assert nivel_desde_T(50).descriptor_verbal == "Medio"
    assert nivel_desde_T(25).descriptor_verbal == "Muy bajo"


# --- criterio de niveles configurable -------------------------------------------------
def _baremo():
    import pandas as pd

    filas = [{"tramo_edad": "49_54", "pd": p, "percentil": pc, "T": t}
             for p, pc, t in [(0, 1, 27), (3, 2, 30), (5, 10, 37), (7, 16, 40), (9, 50, 50),
                              (15, 99, 73)]]
    return pd.DataFrame(filas)


def test_criterio_por_T_equivale_al_historico():
    from grafomotor.scoring.niveles import CriterioNiveles

    c = CriterioNiveles.por_T(2)
    b = _baremo()
    for pd_ in (0, 3, 5, 7, 9, 15):
        from grafomotor.scoring.baremo import pd_a_T

        historico = nivel_desde_T(pd_a_T(pd_, 50, b)["T"], n_clases=2)
        nuevo = c.clasificar(pd_, 50, b)
        assert (nuevo.nivel, nuevo.accion) == (historico.nivel, historico.accion)


def test_criterio_por_percentil_con_tres_niveles():
    from grafomotor.scoring.niveles import Corte, CriterioNiveles

    c = CriterioNiveles("percentil", (Corte("Muy bajo", 2, "derivar"),
                                      Corte("Bajo", 16, "reforzar_y_revaluar"),
                                      Corte("Adecuado", 100, "ninguna")), fuente="prueba")
    b = _baremo()
    assert c.clasificar(3, 50, b).nivel == "Muy bajo"      # percentil 2
    assert c.clasificar(7, 50, b).nivel == "Bajo"          # percentil 16
    assert c.clasificar(9, 50, b).nivel == "Adecuado"      # percentil 50
    assert c.etiquetas == ["Adecuado", "Bajo", "Muy bajo"]
    assert c.en_riesgo(7, 50, b) and not c.en_riesgo(9, 50, b)


def test_criterio_rechaza_cortes_desordenados():
    import pytest

    from grafomotor.scoring.niveles import Corte, CriterioNiveles

    with pytest.raises(ValueError):
        CriterioNiveles("percentil", (Corte("Adecuado", 100, "ninguna"),
                                      Corte("Bajo", 16, "reforzar_y_revaluar")))
    with pytest.raises(ValueError):
        CriterioNiveles("z", (Corte("Adecuado", 100, "ninguna"),))
