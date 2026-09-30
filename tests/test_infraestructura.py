"""CLI, nombres de artefactos, entrada/salida y corrección de Holm."""
from pathlib import Path

import numpy as np
import pytest

from grafomotor.artefactos import Artefactos, es_semilla_extra, nombre_variante
from grafomotor.cli import COMANDOS, _modulo, main
from grafomotor.evaluation.comparacion import holm
from grafomotor.io import a_binaria, guardar_json, leer_gris, leer_json


# --- artefactos -------------------------------------------------------------
def test_nombre_variante():
    assert nombre_variante("resnet18") == "resnet18"
    assert nombre_variante("resnet18", "robusto") == "resnet18_robusto"
    assert nombre_variante("efficientnet_b0", "robusto", 2) == "efficientnet_b0_robusto_s2"


def test_semillas_extra_se_reconocen():
    assert es_semilla_extra("resnet18_robusto_s1")
    assert not es_semilla_extra("resnet18_robusto")
    assert not es_semilla_extra("efficientnet_b0")      # "_b0" no es una semilla


def test_rutas_de_artefactos(tmp_path):
    art = Artefactos(tmp_path / "p", tmp_path / "m", tmp_path / "i")
    assert art.oof_dl("resnet18").name == "oof_dl_resnet18.parquet"
    assert art.modelo_dl_fold("resnet18", 3) == tmp_path / "m" / "dl" / "resnet18" / "fold3.pt"
    assert art.robustez("x", "md").suffix == ".md"
    for v in ("resnet18", "resnet18_s1", "efficientnet_b0"):
        guardar_json({}, art.evaluacion_dl(v))
    assert art.variantes_dl() == ["efficientnet_b0", "resnet18"]


# --- entrada/salida ---------------------------------------------------------
def test_json_ida_y_vuelta_con_tipos_numpy(tmp_path):
    ruta = guardar_json({"a": np.int64(3), "b": np.float32(0.5), "c": np.arange(2),
                         "d": Path("x")}, tmp_path / "sub" / "f.json")
    assert leer_json(ruta) == {"a": 3, "b": 0.5, "c": [0, 1], "d": "x"}


def test_leer_gris_error_claro(tmp_path):
    with pytest.raises(FileNotFoundError, match="no se pudo leer"):
        leer_gris(tmp_path / "no_existe.png")


def test_a_binaria():
    out = a_binaria(np.array([[0, 127, 128, 255]], np.uint8))
    assert out.tolist() == [[0, 0, 255, 255]]


# --- Holm -------------------------------------------------------------------
def test_holm_conocido():
    # p ordenados 0.01, 0.02, 0.04 con m = 3 -> 0.03, 0.04, 0.04 (monótono)
    assert holm({"a": 0.04, "b": 0.01, "c": 0.02}) == {"b": 0.03, "c": 0.04, "a": 0.04}
    assert holm({"x": 0.9, "y": 0.8}) == {"y": 1.0, "x": 1.0}   # recorta en 1


# --- CLI --------------------------------------------------------------------
@pytest.mark.parametrize("nombre", list(COMANDOS))
def test_cada_comando_tiene_la_interfaz(nombre):
    if nombre in {"entrenar-dl", "gradcam", "practicidad", "preparar-dl", "robustez"}:
        pytest.importorskip("torch")
    mod = _modulo(nombre)
    assert isinstance(mod.AYUDA, str) and mod.AYUDA
    assert callable(mod.agregar_argumentos) and callable(mod.ejecutar)


def test_cli_ayuda_general(capsys):
    with pytest.raises(SystemExit) as e:
        main(["--help"])
    assert e.value.code == 0
    assert "entrenar-dl" in capsys.readouterr().out


def test_cli_rechaza_comando_desconocido():
    with pytest.raises(SystemExit) as e:
        main(["no-existe"])
    assert e.value.code == 2
