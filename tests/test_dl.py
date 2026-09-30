"""Modelo B: se salta si no están instaladas las dependencias de DL (requirements-dl.txt)."""
import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("timm")
from torchvision import transforms as T

from grafomotor.dl.aumentos import (
    transformacion_entrenamiento,
    transformacion_evaluacion,
    verificar_sin_volteos,
)
from grafomotor.dl.imagen import preparar_gris
from grafomotor.dl.modelo import RedMultiCabeza


def _foto():
    img = np.full((600, 500), 235, np.uint8)
    img[200:400, 150:154] = 30
    img[200:204, 150:350] = 30
    return img


def test_preparar_imagen_224_gris():
    img, aviso = preparar_gris(_foto())
    assert img.shape == (224, 224) and img.dtype == np.uint8
    assert aviso is None


def test_aumentos_sin_volteos_y_3_canales():
    tf = transformacion_entrenamiento()
    verificar_sin_volteos(tf)
    img, _ = preparar_gris(_foto())
    assert tf(img).shape == (3, 224, 224)
    assert transformacion_evaluacion()(img).shape == (3, 224, 224)


def test_verificador_rechaza_volteos():
    with pytest.raises(AssertionError):
        verificar_sin_volteos(T.Compose([T.RandomHorizontalFlip()]))
    with pytest.raises(AssertionError):
        verificar_sin_volteos(T.Compose([T.RandomRotation(45)]))


@pytest.mark.parametrize("arq", ["resnet18", "efficientnet_b0"])
def test_red_multicabeza_elige_la_cabeza_de_la_figura(arq):
    m = RedMultiCabeza(arq, 15, preentrenada=False).eval()
    x = torch.randn(4, 3, 224, 224)
    fig = torch.tensor([0, 3, 3, 14])
    out = m(x, fig)
    assert out.shape == (4,)
    # la salida para la figura k es la columna k de las 15 cabezas
    with torch.no_grad():
        todas = m.cabezas(m.red(x))
    assert torch.allclose(out, todas[torch.arange(4), fig], atol=1e-5)


def test_fase1_congela_la_red():
    m = RedMultiCabeza("resnet18", 15, preentrenada=False)
    m.congelar_red()
    assert not any(p.requires_grad for p in m.red.parameters())
    assert all(p.requires_grad for p in m.cabezas.parameters())
    ult = m.descongelar_ultimas_capas()
    assert ult and all(p.requires_grad for p in m.red.layer4.parameters())
    assert not any(p.requires_grad for p in m.red.layer1.parameters())


def test_gradcam_devuelve_mapa():
    pytest.importorskip("pytorch_grad_cam")
    from grafomotor.dl.gradcam import atencion_en_trazo, mapa_gradcam

    m = RedMultiCabeza("resnet18", 15, preentrenada=False).eval()
    img, _ = preparar_gris(_foto())
    cam = mapa_gradcam(m, img, figura_idx=2)
    assert cam.shape == (224, 224)
    a = atencion_en_trazo(cam, img)
    assert 0 <= a["frac_en_trazo"] <= 1 and 0 <= a["frac_en_borde"] <= 1
