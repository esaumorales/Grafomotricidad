"""Aislar todo el trazo del niño (F02 tiene dos líneas) y no girar el dibujo al registrar."""
import cv2
import numpy as np

from grafomotor.preprocessing.pipeline import aislar_figura, calidad_imagen, registrar_a_plantilla


def _dos_lineas():
    b = np.zeros((200, 300), np.uint8)
    cv2.line(b, (40, 60), (260, 60), 255, 5)
    cv2.line(b, (40, 140), (260, 140), 255, 5)
    cv2.circle(b, (10, 10), 2, 255, -1)          # mota
    return b


def test_aislar_figura_conserva_las_dos_lineas_y_quita_motas():
    r = aislar_figura(_dos_lineas(), min_area=400)
    assert r[60, 150] == 255 and r[140, 150] == 255
    assert r[10, 10] == 0


def test_registro_por_traslacion_no_gira():
    plantilla = np.zeros((300, 300), np.uint8)
    cv2.line(plantilla, (50, 150), (250, 150), 255, 5)
    inclinada = np.zeros((300, 300), np.uint8)
    cv2.line(inclinada, (50, 100), (250, 200), 255, 5)
    _, reg = registrar_a_plantilla(inclinada, plantilla, "traslacion")
    assert reg["rotacion_deg"] == 0.0


def test_calidad_penaliza_desenfoque():
    g = np.full((200, 300), 235, np.uint8)
    cv2.line(g, (40, 100), (260, 100), 110, 3)
    nitida = calidad_imagen(g)
    borrosa = calidad_imagen(cv2.GaussianBlur(g, (0, 0), 6))
    assert nitida > borrosa
