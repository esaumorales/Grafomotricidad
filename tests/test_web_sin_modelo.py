import argparse
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from grafomotor.config import Config, load_config
from grafomotor.webapp import main


def test_config_del_servidor_se_propaga(monkeypatch, tmp_path):
    from grafomotor.comandos import servir
    import uvicorn

    ruta = tmp_path / "config.yaml"
    ruta.write_text("rutas: {}", encoding="utf-8")
    cfg = load_config(ruta)
    monkeypatch.setenv("GRAFOMOTOR_CONFIG", "anterior")
    monkeypatch.setattr(uvicorn, "run", Mock())
    servir.ejecutar(argparse.Namespace(host="127.0.0.1", puerto=8000, sin_recarga=True), cfg)
    assert load_config().source == ruta.resolve()


def test_historial_funciona_sin_modelo(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "load_config", lambda: Config({"rutas": {"db": str(tmp_path / "app.db")}}))
    monkeypatch.setattr(main, "Servicio", Mock(side_effect=AssertionError("No debe cargar el modelo")))
    assert main.listar_sesiones() == []
    assert main.listar_sesiones_de_nino("prueba") == []


def test_modelo_ausente_da_error_claro(monkeypatch):
    monkeypatch.setattr(main, "_servicio", None)
    monkeypatch.setattr(main, "Servicio", Mock(side_effect=FileNotFoundError("modelo.joblib")))
    with pytest.raises(HTTPException) as error:
        main.servicio()
    assert error.value.status_code == 503
    assert "paquete privado" in error.value.detail
    assert main.salud()["ok"] is False


def test_historial_incluye_percentil_guardado(monkeypatch, tmp_path):
    from grafomotor.webapp import db
    ruta = tmp_path / "historial.db"
    db.iniciar_db(ruta)
    for codigo, percentil in [("INICIO", 20), ("ESPERADO", 65)]:
        db.guardar_sesion(ruta, {
            "child_id": codigo, "edad_meses": 57, "accion": "ninguna",
            "panel_tecnico": {"resumen": {"PD": 4, "nivel": "Adecuado", "percentil": percentil}},
        })
    monkeypatch.setattr(main, "base_sesiones", lambda: ruta)
    filas = {s.child_id: s.percentil for s in main.listar_sesiones()}
    assert filas == {"INICIO": 20, "ESPERADO": 65}
    assert all("resultado_json" not in fila for fila in db.listar_sesiones(ruta))


def test_fecha_nacimiento_se_conserva_en_historial_y_seguimiento(tmp_path):
    from grafomotor.webapp import db
    from grafomotor.webapp.schemas import SesionResumen
    ruta = tmp_path / "fechas.db"
    db.iniciar_db(ruta)
    resultado = {"child_id": "MISMO", "edad_meses": 57, "fecha_nacimiento": "2022-02-03",
                 "accion": "ninguna", "panel_tecnico": {"resumen": {"PD": 4, "nivel": "Adecuado"}}}
    sid = db.guardar_sesion(ruta, resultado)
    assert db.obtener_sesion(ruta, sid)["fecha_nacimiento"] == "2022-02-03"
    for listar in [lambda: db.listar_sesiones(ruta), lambda: db.listar_sesiones_de_nino(ruta, "MISMO")]:
        assert SesionResumen(**listar()[0]).fecha_nacimiento == "2022-02-03"
    resultado.pop("fecha_nacimiento")
    antigua_id = db.guardar_sesion(ruta, resultado)
    antigua = next(f for f in db.listar_sesiones(ruta) if f["id"] == antigua_id)
    assert antigua["fecha_nacimiento"] is None


def test_seguimiento_conserva_estado_por_figura_sin_metricas(tmp_path):
    from grafomotor.webapp import db
    from grafomotor.webapp.schemas import SesionResumen
    ruta = tmp_path / "figuras.db"
    db.iniciar_db(ruta)
    for docente in [None, 1]:
        db.guardar_sesion(ruta, {"child_id": "NINO", "edad_meses": 57, "accion": "ninguna",
            "panel_tecnico": {"resumen": {"PD": 4, "nivel": "Adecuado"}},
            "figuras": [{"figura_id": "F01", "nombre": "línea recta", "puntaje": 0,
                         "puntaje_docente": docente, "decision": "revisar", "indicadores": {"interno": 0.2}}]})
    datos = [SesionResumen(**fila) for fila in db.listar_sesiones_de_nino(ruta, "NINO")]
    assert len(datos) == 2
    assert {fila.figuras[0].puntaje_docente for fila in datos} == {None, 1}
    assert all(fila.figuras[0].decision == "revisar" for fila in datos)
    assert all("indicadores" not in figura for fila in db.listar_sesiones_de_nino(ruta, "NINO") for figura in fila["figuras"])
    assert db.listar_sesiones_de_nino(ruta, "OTRO") == []
