"""Señales conservadoras para pedir una revisión del trazo."""
import cv2


def posible_repeticion(binaria, figura_id):
    if figura_id == "F01":
        _, _, stats, _ = cv2.connectedComponentsWithStats(binaria)
        lineas = [(x, y, w, h) for x, y, w, h, area in stats[1:]
                  if h >= binaria.shape[0] * 0.28 and h >= 4 * w and area >= h]
        for i, (x, y, w, h) in enumerate(lineas):
            for x2, y2, w2, h2 in lineas[i + 1:]:
                separacion = abs((x + w / 2) - (x2 + w2 / 2))
                comun = min(y + h, y2 + h2) - max(y, y2)
                if separacion >= max(w, w2) and comun >= 0.6 * max(h, h2):
                    return "Se ven dos trazos verticales separados. Confirma si se repitió la línea."
    if figura_id == "F04":
        contornos, jerarquia = cv2.findContours(binaria, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        if jerarquia is None:
            return None
        areas = []
        for contorno, datos in zip(contornos, jerarquia[0], strict=True):
            if datos[3] < 0:
                continue
            area = cv2.contourArea(contorno)
            perimetro = cv2.arcLength(contorno, True)
            if area >= binaria.size * 0.012 and perimetro and 4 * 3.14159 * area / perimetro ** 2 >= 0.65:
                areas.append(area)
        areas.sort(reverse=True)
        if len(areas) >= 2 and areas[1] >= 0.55 * areas[0]:
            return "Se ven dos contornos redondeados. Confirma si se repitió el círculo."
    return None
