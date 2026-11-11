from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

from grafomotor.webapp.service import ErrorHoja, Servicio, asignar_paginas


def _servicio():
    servicio = Servicio.__new__(Servicio)
    servicio.plantillas = {f'F{i:02d}': None for i in range(1, 16)}
    servicio._gris = {}
    return servicio


def _hoja(pagina, puntajes=None):
    celda = np.full((40, 60), 230, np.uint8)
    return SimpleNamespace(pagina=pagina, puntajes_pagina=puntajes or {}, copias=[celda] * 5,
                           avisos=[], toca_borde=[False] * 5)


@pytest.mark.parametrize('paginas, numeros', [([3, 3], (1, 2)), ([1, 1], (1, 2))])
def test_aviso_identifica_fotos_con_el_mismo_nombre(paginas, numeros):
    """Con menos de 3 fotos no hay reparto posible: si dos parecen la misma hoja, se avisa."""
    with patch('grafomotor.webapp.service._leer_gris', return_value=np.zeros((2, 2))), patch(
        'grafomotor.webapp.service.segmentar_hoja',
        side_effect=[SimpleNamespace(pagina=pagina) for pagina in paginas],
    ):
        with pytest.raises(ErrorHoja) as error:
            _servicio().recortar_hojas('TEST', [('image.jpg', b'foto') for _ in paginas])
    texto = str(error.value)
    assert all(f'Foto {numero} («image.jpg»)' in texto for numero in numeros)
    pag = paginas[0]
    assert f'figuras {(pag - 1) * 5 + 1} a {pag * 5}' in texto
    assert 'Si muestran hojas distintas' in texto


def test_tres_fotos_dudosas_respetan_el_orden_de_subida():
    """Caso real del 10/11: la Foto 1 (figuras 1-5) se parecía algo más a la página 3 que a la 1.
    Antes salía «la Foto 1 y la Foto 3 son la misma hoja»; ahora cada foto toma su página."""
    puntajes = [{1: 0.30, 2: 0.20, 3: 0.33}, {1: 0.20, 2: 0.60, 3: 0.25}, {1: 0.15, 2: 0.20, 3: 0.65}]
    assert asignar_paginas(puntajes) == [1, 2, 3]


def test_fotos_subidas_en_otro_orden_se_reordenan_si_la_evidencia_es_clara():
    puntajes = [{1: 0.10, 2: 0.15, 3: 0.70}, {1: 0.20, 2: 0.65, 3: 0.20}, {1: 0.68, 2: 0.10, 3: 0.12}]
    assert asignar_paginas(puntajes) == [3, 2, 1]


def test_nunca_repite_pagina_con_tres_fotos():
    rng = np.random.default_rng(0)
    for _ in range(200):
        puntajes = [{p: float(rng.random()) for p in (1, 2, 3)} for _ in range(3)]
        assert sorted(asignar_paginas(puntajes)) == [1, 2, 3]


def test_recortar_hojas_ya_no_falla_por_una_foto_dudosa(tmp_path):
    hojas = [_hoja(3, {1: 0.30, 2: 0.20, 3: 0.33}), _hoja(2, {1: 0.20, 2: 0.60, 3: 0.25}),
             _hoja(3, {1: 0.15, 2: 0.20, 3: 0.65})]
    servicio = _servicio()
    with patch('grafomotor.webapp.service._leer_gris', return_value=np.zeros((2, 2))), patch(
        'grafomotor.webapp.service.segmentar_hoja', side_effect=hojas,
    ), patch.object(Servicio, 'guardar_foto', side_effect=lambda c, f, b, s: Path(tmp_path, f + s)):
        fotos, avisos = servicio.recortar_hojas('TEST', [('image.jpg', b'foto') for _ in hojas])
    assert sorted(fotos) == [f'F{i:02d}' for i in range(1, 16)]
    assert any('Foto 1' in a and 'figuras 1 a 5' in a for a in avisos)
