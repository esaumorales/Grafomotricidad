from datetime import date

import pytest

from grafomotor.scoring.edad import edad_en_meses, edad_valida


@pytest.mark.parametrize("nac,ev,esperado", [
    (date(2020, 9, 2), date(2026, 9, 26), 72),    # ya pasó el día del mes
    (date(2020, 9, 28), date(2026, 9, 26), 71),   # todavía no cumple el mes
    (date(2021, 3, 31), date(2026, 3, 31), 60),   # el mismo día cumple
    (date(2022, 1, 31), date(2022, 3, 1), 1),     # fin de mes
    (date(2023, 5, 10), date(2023, 5, 10), 0),
])
def test_edad_en_meses(nac, ev, esperado):
    assert edad_en_meses(nac, ev) == esperado


def test_evaluacion_antes_del_nacimiento():
    with pytest.raises(ValueError):
        edad_en_meses(date(2026, 1, 2), date(2026, 1, 1))


def test_rango_del_baremo():
    assert edad_valida(36) and edad_valida(78)
    assert not edad_valida(35) and not edad_valida(79)
