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
    if nombre in {"entrenar-dl", "ensamblar-dl", "gradcam", "practicidad", "preparar-dl",
                  "robustez"}:
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


# --- buenas prácticas añadidas ------------------------------------------------
def test_variante_con_resolucion(tmp_path):
    assert nombre_variante("resnet18", lado=320) == "resnet18_320px"
    assert nombre_variante("resnet18", "robusto", 1, 320) == "resnet18_robusto_320px_s1"
    art = Artefactos(tmp_path / "p", tmp_path / "m", tmp_path / "interim_dl")
    assert art.carpeta_dl(224) == tmp_path / "interim_dl"
    assert art.carpeta_dl(320) == tmp_path / "interim_dl_320"
    assert art.lado_de_variante("no_existe") == 224


def test_validacion_anidada_no_mira_el_fold_de_prueba():
    import pandas as pd

    from grafomotor.model.dataset import Datos
    from grafomotor.model.train import ajustar_anidado

    rng = np.random.default_rng(0)
    n = 200
    X = rng.random((n, 6))
    y = (X[:, 0] + rng.normal(0, 0.1, n) > 0.5).astype(int)
    grupos = np.repeat([f"N{i:02d}" for i in range(40)], 5)
    datos = Datos(X, y, grupos, np.array(["F01"] * n), np.full(n, 50), [f"f{i}" for i in range(6)])
    fold = pd.Series(grupos).str[1:].astype(int).to_numpy() % 4
    cfg = {"cv": {"folds": 3}, "grid_search": {"max_depth": [2, 3], "n_estimators": [50]}}
    modelos, params = ajustar_anidado(datos, fold, cfg)
    assert set(modelos) == {0, 1, 2, 3} and set(params) == {0, 1, 2, 3}
    assert all(p["max_depth"] in (2, 3) for p in params.values())


def test_tabla_errores_ordenada_por_confianza():
    import pandas as pd

    from grafomotor.comandos.errores import tabla_errores

    oof = pd.DataFrame({"child_id": ["a", "b", "c", "d"], "figura_id": ["F01"] * 4,
                        "y": [0, 1, 1, 0], "yhat": [1.0, 0.0, 1.0, np.nan],
                        "prob": [0.9, 0.45, 0.8, np.nan]})
    err = tabla_errores(oof)
    assert list(err["child_id"]) == ["a", "b"]          # c acierta, d no se midió
    assert list(err["tipo"]) == ["falso_positivo", "falso_negativo"]
    assert err["confianza"].tolist() == [0.8, 0.1]


def test_acuerdo_evaluadores_perfecto():
    import pandas as pd

    from grafomotor.comandos.acuerdo_evaluadores import tabla_acuerdo

    et = pd.DataFrame({"child_id": ["a", "a", "b"], "figura_id": ["F01", "F02", "F01"],
                       "edad_meses": [50, 50, 60], "puntaje": [1, 0, 1]})
    df = tabla_acuerdo(et, et[["child_id", "figura_id", "puntaje"]])
    assert (df["y"] == df["yhat"]).all()
    with pytest.raises(ValueError):
        tabla_acuerdo(et, et.assign(puntaje=2)[["child_id", "figura_id", "puntaje"]])
