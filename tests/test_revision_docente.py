from types import SimpleNamespace
import pytest
from grafomotor.webapp import db
from grafomotor.webapp.service import Servicio

@pytest.mark.parametrize('puntaje',[0,1])
def test_revision_actualiza_resultado_sin_borrar_prediccion(tmp_path,puntaje):
    servicio=Servicio.__new__(Servicio)
    servicio.db_path=tmp_path/'revision.db'
    db.iniciar_db(servicio.db_path)
    servicio._nivel=lambda total, edad: ({'percentil':50,'tramo':'55_60'},SimpleNamespace(nivel='Ejemplo',accion='ninguna',descriptor_verbal='Ejemplo'))
    resultado={'child_id':'PRUEBA','nombre_nino':None,'edad_meses':60,'accion':'ninguna','figuras':[{'figura_id':'F01','puntaje':0,'puntaje_docente':None,'prob':.4,'decision':'revisar'}],'panel_tecnico':{'resumen':{'PD':0,'PD_ia':0,'nivel':'Ejemplo','nivel_ia':'Ejemplo'}}}
    sid=db.guardar_sesion(servicio.db_path,resultado)
    actualizado=servicio.corregir_figura(sid,'F01',puntaje)
    guardado=db.obtener_sesion(servicio.db_path,sid)
    assert actualizado['panel_tecnico']['resumen']['PD']==puntaje
    assert guardado['figuras'][0]['puntaje_docente']==puntaje
    assert guardado['figuras'][0]['puntaje']==0
    assert guardado['panel_tecnico']['resumen']['PD_ia']==0
