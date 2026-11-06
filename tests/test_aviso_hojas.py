from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

from grafomotor.webapp.service import ErrorHoja, Servicio


@pytest.mark.parametrize('paginas, numeros', [([3, 3], (1, 2)), ([1, 3, 3], (2, 3))])
def test_aviso_identifica_fotos_con_el_mismo_nombre(paginas, numeros):
    servicio = Servicio.__new__(Servicio)
    servicio.plantillas = {}
    servicio._gris = {}
    with patch('grafomotor.webapp.service._leer_gris', return_value=np.zeros((2, 2))), patch(
        'grafomotor.webapp.service.segmentar_hoja',
        side_effect=[SimpleNamespace(pagina=pagina) for pagina in paginas],
    ):
        with pytest.raises(ErrorHoja) as error:
            servicio.recortar_hojas('TEST', [('image.jpg', b'foto') for _ in paginas])
    texto = str(error.value)
    assert all(f'Foto {numero} («image.jpg»)' in texto for numero in numeros)
    assert 'figuras 11 a 15' in texto
    assert 'Si muestran hojas distintas' in texto
