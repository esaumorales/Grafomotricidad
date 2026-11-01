from grafomotor.webapp.observaciones import observaciones

def test_inclinacion_limite():
    r=observaciones('F01', {'angulo':45}, {})
    assert r[0]['revisar'] is False
    assert observaciones('F01', {'angulo':44}, {})[0]['revisar'] is True

def test_cierre_solo_figuras_cerradas():
    assert not any(o['titulo']=='Cierre de la figura' for o in observaciones('F01', {'extremos':2}, {}))
    assert observaciones('F05', {'extremos':2}, {})[0]['revisar'] is True

def test_sin_trazo_y_datos_ausentes():
    assert 'foto' in observaciones('F01', {}, {}, True)[0]['detalle']
    assert observaciones('F01', {'angulo':float('nan')}, {})[0]['titulo']=='Revisión visual necesaria'


def test_imagen_no_fiable_omite_conteos_y_angulos():
    for fid, partes in [('F01', 2), ('F02', 4)]:
        resultado = observaciones(fid, {'partes': partes, 'angulo': 83.2, 'incl_partes': 6.8}, {'partes': 1}, imagen_fiable=False)
        assert len(resultado) == 1
        assert resultado[0]['titulo'] == 'Lectura automática no fiable'
        assert '6.8' not in resultado[0]['detalle']
        assert 'partes separadas' not in resultado[0]['detalle']


def test_componentes_no_se_presentan_como_lineas_confirmadas():
    r = observaciones('F01', {'partes': 2}, {'partes': 1})
    assert 'no un conteo confirmado' in r[0]['detalle']
