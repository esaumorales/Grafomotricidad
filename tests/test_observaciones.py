from grafomotor.webapp.observaciones import GUIAS, observaciones

def test_inclinacion_limite():
    assert observaciones('F01', {'angulo':45}, {})[0]['revisar'] is False
    assert observaciones('F01', {'angulo':44}, {})[0]['revisar'] is True

def test_no_confundir_guia_con_medicion():
    for figura in GUIAS:
        r=observaciones(figura, {}, {})
        assert r[-1]['fuente']=='guia'
    assert not any(o['fuente']=='medicion' for o in observaciones('F03', {'partes':4}, {'partes':1}))

def test_imagen_no_fiable_no_muestra_medidas():
    for fid in ['F01','F02']:
        r=observaciones(fid, {'partes':5,'angulo':83.2,'incl_partes':6.8},{},imagen_fiable=False)
        assert len(r)==1 and r[0]['fuente']=='limitacion'
        assert r[0]['revisar'] is False
        assert 'detalle_tecnico' not in r[0]

def test_grados_en_detalle_opcional():
    r=observaciones('F01', {'angulo':79}, {})[0]
    assert '11.0°' in r['detalle_tecnico']
    assert '°' not in r['detalle']

def test_no_publicar_componentes_como_lineas():
    r=observaciones('F02', {'partes':5}, {'partes':2})
    assert all('componentes' not in o['detalle'] and '5' not in o['detalle'] for o in r)

def test_extremos_no_se_interpretan_como_abertura():
    for figura in ['F04', 'F05', 'F06', 'F10']:
        r=observaciones(figura, {'extremos':2}, {})
        assert all(o['fuente']=='guia' for o in r)
        assert not any('abertura' in o['titulo'] for o in r)
