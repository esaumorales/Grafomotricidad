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
