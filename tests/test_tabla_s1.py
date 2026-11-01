"""El informe solo da como razón de una figura lo que el manual revisa en esa figura (Tabla S1)."""
from grafomotor.explain.tabla_s1 import INDICADORES_POR_FIGURA, aplica, columnas_fuera_del_manual


def test_quince_figuras():
    assert sorted(INDICADORES_POR_FIGURA) == [f"F{i:02d}" for i in range(1, 16)]


def test_cierre_en_circulo_si_en_linea_recta_no():
    assert aplica("cierre", "F04")
    assert not aplica("cierre", "F01")


def test_error_angular_fuera_de_la_linea_ondulada():
    cols = ["error_angular", "dif_angulo", "missingindicator_error_angular", "cr_ondas", "fig_F08"]
    assert columnas_fuera_del_manual("F08", cols) == {"error_angular", "dif_angulo",
                                                      "missingindicator_error_angular"}
    assert columnas_fuera_del_manual("F04", cols) == {"cr_ondas"}


def test_sin_dato_no_filtra():
    assert aplica("proporcion", "F01")
    assert columnas_fuera_del_manual("F99", ["cierre"]) == set()
