"""Describe rasgos visibles del recorte, aparte de la valoración del modelo."""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from scipy.signal import find_peaks

from grafomotor.features.criterios import medir
from grafomotor.io import leer_gris
from grafomotor.preprocessing.hoja import _dice, _fondo, _sin_marco, huella

# Qué se puede reconocer a simple vista y qué comparar cuando la lectura es parcial.
FIGURAS = {
    "F01": ("El trazo se parece a una línea vertical.", "comprueba si hay una sola línea recta de arriba abajo, sin curvas ni cortes"),
    "F02": ("Se distinguen dos líneas horizontales separadas.", "mira si las dos líneas van de lado a lado y se mantienen rectas y separadas"),
    "F03": ("La forma general se parece a una cruz y se distingue el encuentro de los brazos.", "mira si los brazos se unen en el cruce y si alguna línea queda separada"),
    "F04": ("Se aprecia una forma redondeada, parecida a la referencia.", "sigue el borde y comprueba si cierra sin esquinas ni lados rectos; puede ser ovalado"),
    "F05": ("Se aprecia un contorno parecido al cuadrado de referencia.", "revisa el cierre y las cuatro esquinas; los lados pueden tener longitudes distintas"),
    "F06": ("Se aprecia un contorno triangular parecido al de referencia.", "revisa si las tres puntas se unen por lados que se mantienen rectos"),
    "F07": ("La forma general se parece a un aspa y se distingue el encuentro de sus brazos.", "mira si las dos diagonales se cruzan por dentro de las líneas y no en un extremo"),
    "F08": ("El recorrido ondulado del trazo se parece al de la referencia.", "sigue la línea de un extremo al otro y comprueba que mantenga las dos ondas sin interrupciones"),
    "F09": ("Se aprecia un marco con trazos interiores parecidos a los de la referencia.", "revisa el cierre del marco y si las diagonales se cruzan y llegan a las esquinas indicadas en el manual"),
    "F10": ("La silueta se parece al rombo de referencia, con una punta en la parte inferior.", "sigue los cuatro lados y mira si se unen para cerrar el contorno"),
    "F11": ("La forma general se parece a la del círculo sobre el triángulo.", "comprueba si ambas figuras se tocan y si el círculo queda arriba del triángulo"),
    "F12": ("Se aprecia una curva sobre un trazo que se parece a la base de la referencia.", "revisa si la recta y la curva se tocan en un solo punto"),
    "F13": ("La disposición de las curvas se parece a la de la referencia.", "mira si las dos curvas se tocan en el centro, por la parte abultada, sin superponerse"),
    "F14": ("Se aprecia una forma ondulada sobre dos trazos que se parecen a los de referencia.", "comprueba si las rectas se juntan arriba y la curva de tres ondas cruza las dos"),
    "F15": ("La silueta se parece a la referencia, con una parte redondeada hacia abajo y a la derecha.", "revisa dónde se cruzan el cuadrado y el círculo y cuántas esquinas quedan dentro del círculo"),
}
_CONTORNOS = {"F04", "F05", "F06", "F09", "F10"}
_APERTURA = {
    "F04": "revisa si los extremos del contorno se unen; se admite que quede ovalado",
    "F05": "mira si los extremos de los cuatro lados se unen en las esquinas",
    "F06": "comprueba si los tres lados se unen en las puntas",
    "F09": "revisa primero si cierra el marco y luego cómo se cruzan sus diagonales",
    "F10": "sigue los lados hasta la punta inferior y comprueba si el contorno se cierra",
}


@dataclass(frozen=True)
class Componente:
    mascara: np.ndarray
    caja: tuple[int, int, int, int]

    @property
    def largo(self) -> int:
        return max(self.caja[2:])


def _segmentos(tinta: np.ndarray) -> list[Componente]:
    alto, ancho = tinta.shape
    _, etiquetas, datos, _ = cv2.connectedComponentsWithStats(tinta, connectivity=8)
    encontrados = []
    for indice, (x, y, w, h, area) in enumerate(datos[1:], 1):
        if area < max(16, tinta.size * .0005) or max(w, h) < min(alto, ancho) * .09:
            continue
        # El borde de la tabla puede aparecer solo en parte, sin cruzar toda la foto.
        regla_horizontal = (w >= .25 * ancho and w >= 20 * h
                            and (y <= 2 or y + h >= alto - 2))
        regla_vertical = (h >= .55 * alto and h >= 20 * w
                          and (x <= 2 or x + w >= ancho - 2))
        if regla_horizontal or regla_vertical:
            continue
        encontrados.append((area, Componente(etiquetas == indice, (x, y, w, h))))
    encontrados.sort(key=lambda item: item[0], reverse=True)
    if not encontrados:
        return []
    mayor = encontrados[0][0]
    return [parte for area, parte in encontrados if area >= .21 * mayor]


def _bordes(partes: list[Componente]) -> set[str]:
    alto, ancho = partes[0].mascara.shape
    bordes = set()
    for parte in partes:
        x, y, w, h = parte.caja
        if y <= 1:
            bordes.add("superior")
        if y + h >= alto - 1:
            bordes.add("inferior")
        if x <= 1:
            bordes.add("izquierdo")
        if x + w >= ancho - 1:
            bordes.add("derecho")
    return bordes


def _separados(partes: list[Componente]) -> bool:
    if len(partes) != 2:
        return False
    a, b = partes
    distancias = cv2.distanceTransform((~a.mascara).astype(np.uint8), cv2.DIST_L2, 3)
    return float(distancias[b.mascara].min()) > max(4, .055 * min(a.largo, b.largo))


def _linea(parte: Componente, vertical: bool) -> tuple[float, float] | None:
    """Inclinación y desviación de una recta, medidas sobre el centro del lápiz."""
    ys, xs = np.nonzero(parte.mascara)
    avance, desvio = (ys, xs) if vertical else (xs, ys)
    largo = int(np.ptp(avance))
    if largo < 20:
        return None
    bandas = np.linspace(avance.min(), avance.max() + 1, 12)
    centros = [(float(np.mean(avance[grupo])), float(np.median(desvio[grupo])))
               for inicio, fin in zip(bandas[:-1], bandas[1:])
               if (grupo := (avance >= inicio) & (avance < fin)).any()]
    if len(centros) < 9:
        return None
    u, v = np.array(centros).T
    pendiente, base = np.polyfit(u, v, 1)
    desviacion = float(np.percentile(np.abs(v - (pendiente * u + base)), 90)) / largo
    return abs(math.degrees(math.atan(pendiente))), desviacion


def _texto_lineas(figura: str, partes: list[Componente], fuertes: list[Componente]) -> tuple[str, str] | None:
    if len(partes) != len(fuertes) or len(partes) not in {1, 2}:
        return None
    if len(partes) == 2 and (not _separados(partes) or not _separados(fuertes)):
        return None
    vertical = figura == "F01"
    pares = [(_linea(a, vertical), _linea(b, vertical)) for a, b in zip(partes, fuertes)]
    if any(a is None or b is None for a, b in pares):
        return None
    angulos = [max(a[0], b[0]) for a, b in pares]
    desvio_min = [min(a[1], b[1]) for a, b in pares]
    desvio_max = [max(a[1], b[1]) for a, b in pares]
    # Un contorno ancho, un lazo o un grupo de marcas no se describe como línea.
    if max(desvio_max) > .15 or any(
        np.count_nonzero(p.mascara) / max(1, p.caja[2] * p.caja[3]) > .9
        and min(p.caja[2:]) > .12 * p.largo for p in partes
    ):
        return None
    if vertical:
        orientacion = ("casi verticales" if len(partes) == 2 else "casi vertical") if max(angulos) <= 22 else ""
        if len(partes) == 2 and orientacion:
            return ("diferencia", "Se distinguen dos trazos largos, separados y casi verticales. La dirección se parece a la del modelo, que pide una sola línea.")
        if len(partes) == 1 and orientacion and desvio_max[0] <= .024:
            return ("coincidencia", "Se observa una sola línea recta, cercana a la vertical. En cantidad y dirección, el trazo se parece a la línea de referencia.")
        if len(partes) == 1 and desvio_min[0] >= .038:
            return ("diferencia", "Se distingue un trazo principal con una curvatura visible. En la referencia, la línea conserva una dirección recta de principio a fin.")
        if len(partes) == 1 and 25 <= min(a[0] for a in pares[0]) <= max(angulos) <= 42 and desvio_max[0] <= .024:
            return ("coincidencia", "Se ve una sola línea recta. Está inclinada respecto a la vertical de la referencia, pero la inclinación estimada queda dentro del margen que admite el manual.")
        if len(partes) == 1 and min(a[0] for a in pares[0]) > 50 and desvio_max[0] <= .024:
            return ("diferencia", "Se distingue una línea recta con una inclinación marcada. La referencia va de arriba abajo, así que conviene comprobar la orientación de la hoja.")
    elif len(partes) == 2 and max(angulos) <= 22:
        orden = sorted(range(2), key=lambda i: partes[i].caja[1] + partes[i].caja[3] / 2)
        curvadas = [i for i in orden if desvio_min[i] >= .032]
        if curvadas:
            cambio = ("Ambas se curvan en parte del recorrido." if len(curvadas) == 2
                      else f"La de {'arriba' if curvadas[0] == orden[0] else 'abajo'} muestra una curvatura en su recorrido.")
            return ("diferencia", f"Se ven dos líneas aproximadamente horizontales que se mantienen separadas. {cambio} La referencia muestra dos líneas rectas.")
        if max(desvio_max) <= .023:
            return ("coincidencia", "Se ven dos líneas aproximadamente horizontales, rectas y separadas. Su disposición se parece a la referencia, aunque la longitud de las dos líneas puede variar.")
    elif len(partes) == 2 and min(angulos) >= 25 and max(angulos) <= 42 and max(desvio_max) <= .024:
        return ("coincidencia", "Se distinguen dos líneas rectas y separadas. Ambas se inclinan respecto a la horizontal de la referencia; la inclinación estimada se mantiene dentro del margen del manual.")
    elif len(partes) == 1 and max(angulos) <= 22 and desvio_max[0] <= .024:
        return ("parcial", "Se distingue una línea casi horizontal y recta. En el recorte no se distingue con claridad una segunda línea, que sí aparece en la figura de referencia.")
    return None


def _huecos(mascara: np.ndarray) -> list[np.ndarray]:
    contornos, jerarquia = cv2.findContours(mascara.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if jerarquia is None:
        return []
    return [c for i, c in enumerate(contornos)
            if jerarquia[0, i, 3] >= 0 and cv2.contourArea(c) >= max(20, mascara.size * .003)]


def _ajuste_ovalado(puntos: np.ndarray) -> tuple[float, float] | None:
    if len(puntos) < 12:
        return None
    (cx, cy), (a, b), angulo = cv2.fitEllipse(puntos.astype(np.float32))
    if min(a, b) < 4 or not np.isfinite([a, b, cx, cy, angulo]).all():
        return None
    x, y = (puntos - (cx, cy)).T
    coseno, seno = np.cos(np.radians(angulo)), np.sin(np.radians(angulo))
    radio = np.hypot((x * coseno + y * seno) / (a / 2),
                     (-x * seno + y * coseno) / (b / 2))
    return float(np.percentile(np.abs(radio - 1), 85)), max(a, b) / min(a, b)


def _esquinas(contorno: np.ndarray) -> int | None:
    perimetro = cv2.arcLength(contorno, True)
    aproximaciones = {len(cv2.approxPolyDP(contorno, frac * perimetro, True))
                      for frac in (.025, .033, .04)}
    if len(aproximaciones) == 1:
        return aproximaciones.pop()
    return None


def _cruce_simple(parte: Componente) -> bool:
    x, y, w, h = parte.caja
    if min(w, h) < .28 * max(w, h):
        return False
    trazo = parte.mascara[y:y + h, x:x + w]
    # Un marco o un relleno ancho no se describe como dos líneas cruzadas.
    if trazo.mean() > .16 or _huecos(trazo):
        return False
    # La normalización estabiliza el conteo de ramas; aquí no se estiman ángulos.
    binaria = cv2.resize(trazo.astype(np.uint8), (256, 256), interpolation=cv2.INTER_NEAREST)
    medidas = medir(np.pad(binaria, 12) * 255)
    return medidas["cruces"] == 1 and medidas["extremos"] == 4


def _esquinas_de_silueta(parte: Componente) -> list[int]:
    x, y, w, h = parte.caja
    if min(w, h) < .48 * max(w, h):
        return []
    trazo = parte.mascara[y:y + h, x:x + w].astype(np.uint8)
    envolvente = cv2.convexHull(cv2.findNonZero(trazo))
    perimetro = cv2.arcLength(envolvente, True)
    vertices = [len(cv2.approxPolyDP(envolvente, fraccion * perimetro, True))
                for fraccion in (.033, .04, .05)]
    borde = np.ones_like(trazo)
    cv2.polylines(borde, [envolvente], True, 0, 1)
    distancia = cv2.distanceTransform(borde, cv2.DIST_L2, 3)
    cerca_del_borde = distancia[trazo > 0] <= .12 * min(w, h)
    return vertices if cerca_del_borde.mean() >= .70 else []


def _direcciones_cruce(parte: Componente) -> str | None:
    x, y, w, h = parte.caja
    escala = 260 / max(w, h)
    trazo = parte.mascara[y:y+h, x:x+w].astype(np.uint8) * 255
    m = cv2.resize(trazo, (round(w * escala), round(h * escala)), interpolation=cv2.INTER_NEAREST)
    rectas = cv2.HoughLinesP(m, 1, np.pi / 180, 24, minLineLength=round(.45 * min(m.shape)), maxLineGap=4)
    if rectas is None:
        return None
    angulos = [math.degrees(math.atan2(int(y1 - y0), int(x1 - x0))) % 180
               for x0, y0, x1, y1 in rectas.reshape(-1, 4)]
    ejes = (any(min(a, 180 - a) <= 14 for a in angulos)
            and any(abs(a - 90) <= 14 for a in angulos))
    diagonales = (any(28 <= a <= 62 for a in angulos)
                  and any(118 <= a <= 152 for a in angulos))
    if ejes != diagonales:
        return "ejes" if ejes else "diagonales"
    return None


def _punta_visible(mascara: np.ndarray) -> bool:
    x, y, w, h = cv2.boundingRect(mascara.astype(np.uint8))
    if min(w, h) < 30:
        return False
    trazo = mascara[y:y+h, x:x+w].astype(np.uint8) * 255
    escala = 256 / max(w, h)
    m = cv2.resize(trazo, (round(w * escala), round(h * escala)), interpolation=cv2.INTER_NEAREST)
    rectas = cv2.HoughLinesP(m, 1, np.pi / 180, 22, minLineLength=round(.29 * m.shape[0]), maxLineGap=6)
    if rectas is None:
        return False
    lados = {1: [], -1: []}
    for x0, y0, x1, y1 in rectas.reshape(-1, 4):
        if y0 > y1:
            x0, y0, x1, y1 = x1, y1, x0, y0
        dx, dy = int(x1 - x0), int(y1 - y0)
        if dy < .26 * m.shape[0] or abs(dx) < .12 * dy or abs(dx) > 1.7 * dy:
            continue
        lados[1 if dx > 0 else -1].append((x0, y0))
    return any(max(a[1], b[1]) < .33 * m.shape[0] and math.dist(a, b) < .13 * m.shape[0]
               for a in lados[1] for b in lados[-1])


def _apiladas(mascara: np.ndarray, lados_abajo: int) -> bool:
    huecos = sorted(_huecos(mascara), key=lambda c: cv2.boundingRect(c)[1])
    if len(huecos) != 2:
        return False
    arriba, abajo = huecos
    x, y, ancho, alto = cv2.boundingRect(arriba)
    xb, yb, anchob, _ = cv2.boundingRect(abajo)
    traslape = min(x + ancho, xb + anchob) - max(x, xb)
    ajuste = _ajuste_ovalado(arriba.reshape(-1, 2))
    return (yb >= y + .65 * alto and traslape >= .60 * min(ancho, anchob)
            and ajuste is not None and ajuste[0] <= .19 and ajuste[1] <= 2.5
            and _esquinas(abajo) == lados_abajo)


def _hueco_entre_curvas(mascara: np.ndarray) -> bool:
    huecos = _huecos(mascara)
    if len(huecos) != 1:
        return False
    x, _, ancho, alto = cv2.boundingRect(mascara.astype(np.uint8))
    hx, _, hw, _ = cv2.boundingRect(huecos[0])
    centro = (hx + hw / 2 - x) / ancho
    return .25 <= centro <= .75 and cv2.contourArea(huecos[0]) < .25 * ancho * alto


def _perfil_horizontal(mascara: np.ndarray) -> np.ndarray | None:
    """Altura del trazo en 25 tramos, cuando cada tramo tiene un centro claro."""
    ys, xs = np.nonzero(mascara)
    if not len(xs):
        return None
    ancho, alto = np.ptp(xs), np.ptp(ys)
    if ancho < 35 or alto < .10 * ancho:
        return None
    cortes = np.linspace(xs.min(), xs.max() + 1, 26)
    perfil = []
    for i, (inicio, fin) in enumerate(zip(cortes[:-1], cortes[1:])):
        tramo = ys[(xs >= inicio) & (xs < fin)]
        if len(tramo) < 3 or (0 < i < 24 and np.ptp(tramo) > .48 * alto):
            return None
        perfil.append(np.median(tramo))
    return (np.array(perfil) - ys.min()) / max(alto, 1)


def _giros_onda(mascara: np.ndarray) -> int | None:
    perfil = _perfil_horizontal(mascara)
    if perfil is None:
        return None
    perfil = np.convolve(np.pad(perfil, 1, mode="edge"), np.ones(3) / 3, mode="valid")
    picos, _ = find_peaks(perfil, prominence=.15, distance=3)
    valles, _ = find_peaks(-perfil, prominence=.15, distance=3)
    return len(picos) + len(valles)


def _curva_en_u(mascara: np.ndarray) -> bool:
    perfil = _perfil_horizontal(mascara)
    if perfil is None:
        return False
    fondo = np.median(perfil[9:16])
    return fondo > .69 and max(np.median(perfil[:3]), np.median(perfil[-3:])) < fondo - .25


def _partes_lado_a_lado(partes: list[Componente]) -> bool:
    if not _separados(partes):
        return False
    a, b = sorted((parte.caja for parte in partes), key=lambda caja: caja[0])
    xa, ya, wa, ha = a
    xb, yb, wb, hb = b
    alto_comun = min(ya + ha, yb + hb) - max(ya, yb)
    return xa + wa < xb and alto_comun > .55 * min(ha, hb)


def _encerrados(mascara: np.ndarray) -> tuple[int, int | None]:
    huecos = _huecos(mascara)
    esquinas = _esquinas(huecos[0]) if len(huecos) == 1 else None
    return len(huecos), esquinas


def _contorno_rombo(mascara: np.ndarray) -> str | None:
    huecos = _huecos(mascara)
    if len(huecos) != 1:
        return None
    contorno = huecos[0]
    envolvente = cv2.convexHull(contorno)
    poligono = cv2.approxPolyDP(envolvente, .033 * cv2.arcLength(envolvente, True), True).reshape(-1, 2)
    x, y, ancho, alto = cv2.boundingRect(contorno)
    if min(ancho, alto) < 22 or not .45 <= ancho / alto <= 2:
        return None
    bajos = poligono[poligono[:, 1] >= y + .86 * alto]
    if len(bajos) >= 2 and np.ptp(bajos[:, 0]) >= .32 * ancho:
        return "base"
    if len(bajos) == 1 and x + .22 * ancho < bajos[0, 0] < x + .78 * ancho:
        if _esquinas(envolvente) == 4:
            return "cuatro"
        if len(poligono) >= 5:
            return "punta"
    return None


def _lado_vertical_derecho(mascara: np.ndarray) -> bool:
    x, _, ancho, alto = cv2.boundingRect(mascara.astype(np.uint8))
    lado = mascara.copy()
    lado[:, :x + round(.78 * ancho)] = False
    caja = cv2.boundingRect(lado.astype(np.uint8))
    if caja[3] < .58 * alto:
        return False
    linea = _linea(Componente(lado, caja), True)
    return linea is not None and linea[0] <= 20 and linea[1] <= .04


def _dos_partes_superpuestas(mascara: np.ndarray) -> bool:
    """Dos contornos que encierran tres regiones, incluida la parte compartida."""
    zonas = _huecos(mascara)
    if len(zonas) != 3:
        return False
    areas = sorted(cv2.contourArea(z) for z in zonas)
    return areas[0] >= .07 * areas[2] and areas[0] <= .72 * areas[2]


def _detalles_visibles(
    figura: str, lecturas: tuple[list[Componente], list[Componente]],
    mascaras: tuple[np.ndarray, np.ndarray], referencia: np.ndarray,
) -> tuple[str, str, str] | None:
    """Observaciones específicas confirmadas en dos lecturas de contraste."""
    if figura == "F08" and all(len(p) == 1 for p in lecturas):
        giros = [_giros_onda(m) for m in mascaras]
        del_modelo = _giros_onda(referencia)
        if giros[0] is not None and giros[0] == giros[1] and del_modelo:
            if giros[0] > del_modelo:
                return ("diferencia", "Se ve una línea continua que sube y baja más veces que la referencia. El dibujo conserva el movimiento ondulado, pero añade cambios de dirección a lo largo del recorrido.",
                        "sigue la línea desde el inicio y compara cuántas subidas y bajadas aparecen")
            if giros[0] == del_modelo:
                return ("coincidencia", "Se ve una línea continua con la misma cantidad de subidas y bajadas visibles que la referencia. Las curvas pueden verse más anchas o más estrechas. Recorre el dibujo desde un extremo para comparar el orden de las ondas.",
                        "compara el orden y la dirección de las curvas")
            if giros[0] > 0:
                return ("diferencia", "Se distingue una curva amplia, con menos subidas y bajadas visibles que en la referencia. Mira dónde empieza y termina la línea para comparar el recorrido completo.",
                        "comprueba si aparece la segunda curvatura del modelo")
    if figura == "F10" and len(lecturas[0]) == len(lecturas[1]) >= 2:
        if all(not _huecos(m) for m in mascaras):
            return ("diferencia", "Se ven varios segmentos que se acercan, pero en la foto quedan espacios entre partes del dibujo. En la referencia, los cuatro lados se unen para formar un solo contorno.",
                    "revisa en la hoja original si los segmentos llegan a unirse en las puntas")
    if figura == "F10" and all(len(p) == 1 for p in lecturas):
        formas = [_contorno_rombo(m) for m in mascaras]
        if formas == ["cuatro", "cuatro"]:
            return ("coincidencia", "Se distinguen cuatro esquinas y un contorno cerrado que termina en una punta hacia abajo. Esa disposición coincide con la forma general del rombo. Los lados pueden variar de longitud.",
                    "mira cómo se unen los lados en las cuatro puntas")
        if formas == ["punta", "punta"]:
            return ("diferencia", "Se ve una punta abajo, como en el rombo de referencia. Hacia arriba el contorno cambia de dirección de forma más suave y las otras puntas quedan menos marcadas.",
                    "compara la parte superior y ambos costados con las cuatro puntas del modelo")
        if formas == ["base", "base"]:
            return ("diferencia", "Se distingue un contorno cerrado que termina abajo en un tramo ancho. En la referencia los lados inferiores se encuentran en una sola punta.",
                    "fíjate en cómo se unen los lados de abajo")
    if figura == "F09" and all(len(p) == 1 for p in lecturas):
        interiores = [_encerrados(m) for m in mascaras]
        if interiores == [(1, 4), (1, 4)]:
            return ("diferencia", "Se distingue un marco cerrado de cuatro lados. La zona interior se ve como un solo espacio y no se distingue el cruce que divide el interior en la referencia.",
                    "comprueba si las diagonales aparecen dentro del marco en la hoja original")
        if all(n == 4 for n, _ in interiores):
            return ("coincidencia", "Se distinguen cuatro espacios dentro del contorno, separados por los trazos interiores. Esa división se parece a la que forman las diagonales en el marco de referencia.",
                    "comprueba a qué esquinas llegan las diagonales")
    if figura == "F11" and all(_apiladas(m, 3) for m in mascaras):
        return ("coincidencia", "Se distingue una forma redondeada en la parte superior y un contorno de tres lados debajo. El orden de las dos partes se parece al de la referencia.",
                "mira si el círculo y la punta del triángulo se tocan")
    if figura == "F12":
        if all(len(p) == 1 and _curva_en_u(p[0].mascara) for p in lecturas):
            return ("diferencia", "Se ve una curva que baja y vuelve a subir, parecida a la del modelo. Debajo de la curva no se distingue la línea de base que aparece en la referencia.",
                    "busca si hay una base visible y si toca la parte baja de la curva")
        if all(len(p) == 2 and _separados(p) for p in lecturas):
            def curva_y_base(partes: list[Componente]) -> bool:
                curva, base = sorted(partes, key=lambda parte: parte.caja[1])
                linea = _linea(base, False)
                return bool(linea and linea[0] < 18 and linea[1] < .045
                            and _curva_en_u(curva.mascara)
                            and base.caja[1] >= curva.caja[1] + .65 * curva.caja[3])
            if all(curva_y_base(p) for p in lecturas):
                return ("diferencia", "Se ve una curva arriba y una línea de lado a lado debajo. Se distingue un espacio entre ambas en la foto. En la referencia se tocan en la parte más baja de la curva.",
                        "mira si la hoja original muestra un punto de contacto")
    if figura == "F13" and all(_partes_lado_a_lado(p) for p in lecturas):
        return ("diferencia", "Se ven dos trazos, uno al lado del otro, con un espacio entre ellos. La referencia muestra dos curvas que se acercan hasta tocarse en el centro.",
                "mira si las partes abultadas llegan a tocarse o si queda un espacio")
    if figura == "F13" and not _huecos(referencia) and all(_hueco_entre_curvas(m) for m in mascaras):
        return ("diferencia", "Cerca del encuentro de los trazos aparece un pequeño espacio rodeado por lápiz. La referencia tiene dos curvas que se tocan en un punto sin encerrar un espacio entre ellas.",
                "observa si las curvas se tocan en un punto o se cruzan")
    if figura == "F14" and all(_punta_visible(m) for m in mascaras):
        return ("parcial", "Se distinguen dos lados que se acercan hasta formar una punta arriba. Esa parte se parece a la referencia. El recorrido completo de la curva requiere una mirada por separado.",
                "sigue la curva y comprueba si tiene tres ondas y cruza los dos lados")
    if figura == "F15" and all(_dos_partes_superpuestas(m) for m in mascaras):
        return ("parcial", "Se distinguen tres espacios encerrados por los trazos. Esa división también aparece cuando se superponen los contornos del cuadrado y el círculo en la referencia.",
                "mira si el círculo queda abajo a la derecha y cuántas esquinas del cuadrado quedan dentro")
    return None


def _arco_ovalado(puntos: np.ndarray, tolerancia: float) -> bool:
    if len(puntos) < 12:
        return False
    ancho, alto = np.ptp(puntos, axis=0)
    if min(ancho, alto) < 20:
        return False
    ajuste = _ajuste_ovalado(puntos)
    return ajuste is not None and ajuste[0] <= tolerancia and ajuste[1] <= 2.2


def _figuras_apiladas_visibles(partes: list[Componente]) -> bool:
    if len(partes) != 2:
        return False
    arriba, abajo = sorted(partes, key=lambda p: p.caja[1])
    x, y, w, h = arriba.caja
    xb, yb, wb, _ = abajo.caja
    traslape = min(x + w, xb + wb) - max(x, xb)
    if yb < y + .75 * h or traslape < .30 * min(w, wb):
        return False
    puntos = np.argwhere(arriba.mascara[:y + round(h / 2)])[::5, ::-1]
    esquinas = _esquinas_de_silueta(abajo)
    return (_arco_ovalado(puntos, .19) and not _huecos(arriba.mascara)
            and esquinas.count(3) >= 2)


def _dos_tramos_verticales(partes: list[Componente]) -> bool:
    if not _separados(partes):
        return False
    if any("inferior" not in _bordes([parte]) for parte in partes):
        return False
    lineas = [_linea(parte, True) for parte in partes]
    if any(linea is None for linea in lineas):
        return False
    angulos = sorted(linea[0] for linea in lineas)
    return angulos[0] <= 6 and 10 <= angulos[1] <= 24 and max(l[1] for l in lineas) <= .032


def _arco_izquierdo_y_extension(mascara: np.ndarray) -> bool:
    x, _, w, h = cv2.boundingRect(mascara.astype(np.uint8))
    if w < 1.4 * h:
        return False
    izquierda = mascara[:, :x + round(.34 * w)]
    derecha = mascara[:, x + round(.53 * w):]
    puntos = np.argwhere(izquierda)[::5, ::-1]
    return _arco_ovalado(puntos, .12) and np.count_nonzero(derecha) > .20 * np.count_nonzero(mascara)


def _centro_hueco(mascara: np.ndarray) -> float | None:
    huecos = _huecos(mascara)
    if len(huecos) != 1:
        return None
    x, _, w, _ = cv2.boundingRect(mascara.astype(np.uint8))
    hx, _, hw, _ = cv2.boundingRect(huecos[0])
    return (hx + hw / 2 - x) / w


def _recta_arriba_arco_abajo(mascara: np.ndarray) -> bool:
    x, y, w, h = cv2.boundingRect(mascara.astype(np.uint8))
    arriba = mascara[:y + round(.12 * h)]
    caja = cv2.boundingRect(arriba.astype(np.uint8))
    linea = _linea(Componente(arriba, caja), False)
    huecos = _huecos(mascara)
    if not linea or linea[0] > 12 or linea[1] > .035 or caja[2] < .65 * w or len(huecos) != 1:
        return False
    contorno = huecos[0]
    _, hy, hw, hh = cv2.boundingRect(contorno)
    if hy < y + .23 * h or hw < .28 * w:
        return False
    puntos = contorno.reshape(-1, 2)
    return _arco_ovalado(puntos[puntos[:, 1] < hy + .72 * hh], .10)


def _detalle_compuesto(
    figura: str, partes: tuple[list[Componente], list[Componente]],
    mascaras: tuple[np.ndarray, np.ndarray], bordes: set[str], referencia: np.ndarray,
) -> tuple[str, str, str] | None:
    if figura == "F11" and "superior" in bordes and all(_figuras_apiladas_visibles(p) for p in partes):
        return ("recorte", "Se ve un trazo redondeado arriba y una forma triangular debajo, en el mismo orden que en la referencia. El trazo de arriba llega al borde del recorte y no se distingue si cierra ni si toca la punta del triángulo.",
                "mira dónde termina el contorno de arriba y si llega a tocar el de abajo")
    if figura == "F12" and "inferior" in bordes and all(_dos_tramos_verticales(p) for p in partes):
        return ("recorte", "Se ven dos trazos largos y separados. Uno va casi de arriba abajo y el otro está más inclinado. Los dos llegan al borde inferior. En lo visible no aparece la línea horizontal que sirve de base en la referencia.",
                "busca la base y el punto donde se une con la curva")
    if figura == "F13" and "inferior" in bordes and all(_arco_izquierdo_y_extension(m) for m in mascaras):
        return ("recorte", "A la izquierda se distingue un arco redondeado. Los trazos se extienden también hacia la derecha y llegan al borde inferior del recorte. Se ve la disposición de lado a lado, aunque queda por comprobar cómo se encuentran las curvas.",
                "fíjate si se tocan en un punto o se superponen")
    if figura == "F14" and bordes:
        centro_ref = _centro_hueco(referencia)
        centros = [_centro_hueco(m) for m in mascaras]
        if centro_ref is not None and all(c is not None and c > centro_ref + .18 for c in centros):
            return ("recorte", "En el recorte se ve un espacio cerrado hacia la derecha, formado donde se encuentran varios trazos. En la referencia ese espacio queda más centrado. Parte del dibujo llega al borde de la foto.",
                    "sigue la curva completa y mira dónde cruza los dos lados")
    if figura == "F15" and not bordes and all(_recta_arriba_arco_abajo(m) for m in mascaras):
        return ("parcial", "Se ve un tramo casi horizontal arriba y un arco más abajo. El arco y otros trazos se unen y encierran un espacio. Todavía cuesta seguir por separado el contorno del cuadrado y el del círculo.",
                "sigue ambos bordes y comprueba dónde se cruzan y qué esquina queda dentro del círculo")
    return None


def _triangulo_con_lado_curvo_y_abertura(partes: list[Componente]) -> bool:
    if len(partes) != 2:
        return False
    izquierda, derecha = sorted(partes, key=lambda p: p.caja[0])
    _, yi, wi, hi = izquierda.caja
    _, y, w, h = derecha.caja
    if h < 50 or abs(yi - y) > .16 * h or not .75 <= hi / h <= 1.25 or wi >= .60 * w:
        return False
    lado_izquierdo = _linea(izquierda, True)
    if not lado_izquierdo or not 12 <= lado_izquierdo[0] <= 45 or lado_izquierdo[1] > .05:
        return False
    lado_derecho = derecha.mascara[:y + round(.80 * h)]
    medicion = _linea(Componente(lado_derecho, cv2.boundingRect(lado_derecho.astype(np.uint8))), True)
    base = derecha.mascara[y + round(.76 * h):y + h]
    if not medicion or not .085 <= medicion[1] <= .20 or cv2.boundingRect(base.astype(np.uint8))[2] < .45 * w:
        return False

    def distancia_en(inicio: float, fin: float) -> float:
        filas = slice(y + round(inicio * h), y + round(fin * h))
        a, b = izquierda.mascara[filas], derecha.mascara[filas]
        if not a.any() or not b.any():
            return math.inf
        distancias = cv2.distanceTransform((~a).astype(np.uint8), cv2.DIST_L2, 5)
        return float(distancias[b].min())

    arriba, abajo = distancia_en(0, .23), distancia_en(.76, 1)
    return arriba <= .07 * w and .07 * w <= abajo <= .25 * w and abajo > 1.8 * arriba


def _quiebre_superior_derecho(parte: Componente) -> bool:
    x, y, w, h = parte.caja
    contornos, _ = cv2.findContours(parte.mascara.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    borde = max(contornos, key=cv2.contourArea)
    if len(borde) < 5:
        return False
    envolvente = cv2.convexHull(borde, returnPoints=False)
    try:
        quiebres = cv2.convexityDefects(borde, envolvente)
    except cv2.error:
        return False
    if quiebres is None:
        return False
    for _, _, indice, distancia in quiebres.reshape(-1, 4):
        px, py = borde[indice, 0]
        if px > x + .65 * w and py < y + .25 * h and .045 * w <= distancia / 256 <= .16 * w:
            return True
    return False


def describir_trazo(figura: str, ruta: str | Path, referencia: np.ndarray) -> dict[str, str]:
    """Devuelve una observación de la foto y un punto concreto para revisar."""
    parecido, criterio = FIGURAS[figura]
    resultado = {"criterio": criterio}

    def describir(estado: str, texto: str) -> dict[str, str]:
        return {**resultado, "estado": estado, "texto": texto}

    gris = leer_gris(ruta)
    if max(gris.shape) > 1200:
        escala = 1200 / max(gris.shape)
        gris = cv2.resize(gris, None, fx=escala, fy=escala, interpolation=cv2.INTER_AREA)
    normalizada = cv2.divide(cv2.GaussianBlur(gris, (3, 3), 0), _fondo(gris), scale=255)
    corte, _ = cv2.threshold(normalizada, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    corte = min(237, corte)
    partes = _segmentos((normalizada <= corte).astype(np.uint8))
    fuertes = _segmentos((normalizada <= corte - 9).astype(np.uint8))
    if not partes or not fuertes:
        return describir("insuficiente", "Las marcas se ven tenues en la foto. La hoja original puede ayudar a ver mejor el trazo.")
    mascara = np.logical_or.reduce([p.mascara for p in partes])
    mascara_fuerte = np.logical_or.reduce([p.mascara for p in fuertes])
    bordes = _bordes(partes) & _bordes(fuertes)
    if figura in {"F03", "F07", "F09"} and len(partes) == len(fuertes) == 1:
        if _cruce_simple(partes[0]) and _cruce_simple(fuertes[0]):
            if figura == "F09":
                resultado["criterio"] = ("en la hoja original, comprueba si hay un marco cerrado alrededor del cruce"
                                         if bordes else "busca si hay un marco cerrado alrededor del cruce")
                texto = ("Se ven dos líneas que se cruzan. En la parte visible no se distingue el marco de cuatro lados que rodea las diagonales en la referencia.")
                if bordes:
                    texto += " Uno de los brazos llega al borde del recorte."
                return describir("diferencia", texto)
            direccion = _direcciones_cruce(partes[0])
            if direccion is not None and direccion == _direcciones_cruce(fuertes[0]):
                espera_ejes = figura == "F03"
                coincide = (direccion == "ejes") == espera_ejes
                orientacion = ("un trazo casi vertical y otro de lado a lado" if direccion == "ejes"
                               else "dos brazos oblicuos que forman un aspa")
                esperado = ("una línea de arriba abajo y otra de lado a lado" if espera_ejes
                            else "dos diagonales que se encuentran")
                resultado["criterio"] = "mira cómo se unen los brazos en el punto de encuentro"
                if coincide:
                    return describir("coincidencia", f"Se ve un cruce con {orientacion}. Tanto el encuentro como la dirección general de los brazos se parecen a la referencia.")
                return describir("diferencia", f"Los trazos sí se encuentran. Se distingue un cruce con {orientacion}. La referencia muestra {esperado}; ese es el detalle que cambia al comparar los dos dibujos.")
            resultado["criterio"] = "compara la dirección de los brazos con la referencia"
            return describir("coincidencia", "Se distinguen dos líneas que se encuentran en un punto, con brazos visibles a ambos lados del cruce. Ese encuentro es el rasgo principal que comparte con la figura de referencia.")
    if figura == "F06" and not bordes and all(_triangulo_con_lado_curvo_y_abertura(p) for p in (partes, fuertes)):
        resultado["criterio"] = "revisa en la hoja si la base llega a unirse con el lado izquierdo"
        return describir("diferencia", "Se reconoce la forma general de un triángulo, con una punta arriba y una base. El lado derecho se curva y, en la esquina inferior izquierda, se ve un pequeño espacio entre la base y el otro lado.")
    if figura == "F06" and not bordes and len(partes) == len(fuertes) == 1:
        siluetas = [_esquinas_de_silueta(p[0]) for p in (partes, fuertes)]
        if all(min(vertices, default=0) >= 4 for vertices in siluetas):
            resultado["criterio"] = "compara los cambios de dirección del contorno con los tres lados rectos del modelo"
            return describir("diferencia", "Se distingue un contorno con una base y varios cambios de dirección. En la foto no se ven tres puntas claras como las del triángulo de referencia.")
        if siluetas == [[3, 3, 3], [3, 3, 3]] and not _huecos(mascara) and not _huecos(mascara_fuerte):
            resultado["criterio"] = _APERTURA[figura]
            return describir("parcial", "Se distingue una silueta con tres puntas, como en la referencia. La foto no deja ver un contorno completamente cerrado. Una unión tenue o un espacio entre los extremos pueden producir esa apariencia.")
    if figura == "F11" and all(_apiladas(m, 4) for m in (mascara, mascara_fuerte)):
        resultado["criterio"] = "revisa si la parte de abajo tiene una punta superior, como el triángulo del modelo"
        return describir("diferencia", "Se distingue una forma redondeada arriba, en la posición que muestra el modelo. Debajo se ve un contorno con cuatro esquinas, distinto del triángulo de tres puntas que se espera.")
    ref = _sin_marco(referencia)
    compuesto = _detalle_compuesto(figura, (partes, fuertes), (mascara, mascara_fuerte), bordes, ref)
    if compuesto:
        estado, texto, criterio = compuesto
        resultado["criterio"] = criterio
        return describir(estado, texto)
    if not bordes:
        detalle = _detalles_visibles(figura, (partes, fuertes), (mascara, mascara_fuerte), ref)
        if detalle:
            estado, texto, criterio = detalle
            resultado["criterio"] = criterio
            return describir(estado, texto)
    if figura == "F09" and bordes == {"izquierdo"} and min(len(partes), len(fuertes)) >= 2:
        if all(not _huecos(m) and _lado_vertical_derecho(m) for m in (mascara, mascara_fuerte)):
            resultado["criterio"] = "comprueba si el marco se cierra y si se ve el cruce de las diagonales"
            return describir("recorte", "Se ve un tramo casi vertical a la derecha y otros trazos que llegan al borde izquierdo. En la parte visible no se distingue un marco cerrado. Como el recorte corta parte del dibujo, tampoco se puede confirmar el cruce de las diagonales.")
    if figura == "F01" and "inferior" in bordes and corte >= 218:
        principales = [_linea(p[0], True) for p in (partes, fuertes) if len(p) > 1]
        if len(principales) == 2 and all(l and l[0] <= 12 and l[1] <= .025 for l in principales):
            resultado["criterio"] = "comprueba si las marcas de al lado forman parte del trazo o si solo hay una línea"
            return describir("recorte", "Se ve una línea casi vertical y algunas marcas tenues a su lado. Una de esas marcas llega al borde inferior de la foto.")
    if figura == "F05" and not bordes and len(partes) == len(fuertes) == 1:
        if all(_quiebre_superior_derecho(p[0]) for p in (partes, fuertes)):
            resultado["criterio"] = "compara ese tramo con la esquina y el lado derecho de la referencia"
            return describir("diferencia", "Se aprecia el contorno general del cuadrado. Cerca de la esquina superior derecha, el trazo hace un pequeño quiebre antes de continuar hacia abajo.")
    if bordes:
        visible = "Se distingue parte del trazo"
        if figura == "F04":
            ajuste = _ajuste_ovalado(np.argwhere(mascara)[::5, ::-1])
            if ajuste and ajuste[0] <= .16 and ajuste[1] <= 2.5:
                visible = "Se aprecia una forma redondeada, parecida a un óvalo"
        borde = f"borde {next(iter(bordes))}" if len(bordes) == 1 else "borde de la imagen"
        return describir("recorte", f"{visible}. El trazo llega al {borde} y el recorte no deja ver la figura completa.")
    if figura in {"F01", "F02"}:
        lineas = _texto_lineas(figura, partes, fuertes)
        if lineas:
            return describir(*lineas)
    if figura not in {"F01", "F02"} and _separados(partes) and _separados(fuertes):
        if len(_segmentos((ref > 0).astype(np.uint8))) == 1:
            return describir("diferencia", "En la foto se distinguen dos partes del trazo con un espacio visible entre ellas. El trazo de referencia forma un conjunto unido. Mira en la hoja original si hay un trazo tenue entre ambas.")
        return describir("parcial", "En la foto se distinguen dos partes separadas. Compáralas con la referencia para saber si corresponden a las partes del modelo y si están colocadas como se espera.")
    huella_ref = huella(ref)
    similitud = min(_dice(huella(m.astype(np.uint8) * 255), huella_ref)
                    for m in (mascara, mascara_fuerte))
    if figura in _CONTORNOS and len(partes) == len(fuertes) == 1:
        interior = _huecos(mascara)
        interior_fuerte = _huecos(mascara_fuerte)
        if figura == "F04" and len(interior) == len(interior_fuerte) == 1:
            puntos = [cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0]
                      for m in (mascara, mascara_fuerte)]
            ajustes = [_ajuste_ovalado(max(c, key=cv2.contourArea).reshape(-1, 2)) for c in puntos]
            if all(a and a[0] <= .09 and a[1] <= 2.5 for a in ajustes):
                if all(a[1] >= 1.23 for a in ajustes):
                    return describir("coincidencia", "El trazo forma un contorno cerrado y redondeado. Se ve más alargado que la referencia, y el manual permite que el círculo tenga forma ovalada.")
                return describir("coincidencia", "El trazo forma un contorno redondeado y cerrado. La forma general se parece a la referencia y se distingue un espacio interior rodeado por el lápiz.")
            esquinas = _esquinas(interior[0])
            if esquinas in {3, 4} and esquinas == _esquinas(interior_fuerte[0]):
                return describir("diferencia", "Se ve un contorno cerrado, con cambios de dirección marcados en el borde. La referencia mantiene una curva continua, sin esquinas.")
        if figura == "F05" and len(interior) == len(interior_fuerte) == 1:
            esquinas = _esquinas(interior[0])
            if esquinas in {5, 6} and esquinas == _esquinas(interior_fuerte[0]):
                return describir("diferencia", "Se distingue un contorno cerrado con más de cuatro cambios de dirección visibles. En el cuadrado de referencia, el borde cambia de dirección en cuatro esquinas.")
        lados = {"F05": 4, "F06": 3, "F10": 4}.get(figura)
        if lados and len(interior) == len(interior_fuerte) == 1 and similitud >= .58:
            if _esquinas(interior[0]) == _esquinas(interior_fuerte[0]) == lados:
                numero = "tres" if lados == 3 else "cuatro"
                return describir("coincidencia", f"Se distingue un contorno cerrado con {numero} esquinas visibles. Eso se parece a la estructura de referencia; mira también cómo se unen los lados.")
        if not interior and not interior_fuerte and similitud >= .55:
            resultado["criterio"] = _APERTURA[figura]
            return describir("parcial", "La forma general se parece a la referencia, pero en la foto no se distingue un contorno que se cierre por completo. Una parte tenue o interrumpida puede hacer difícil ver la unión.")
    # Para figuras de varios trazos, la semejanza de la silueta es solo una pista.
    if figura not in {"F01", "F02", "F04"} and similitud >= .73:
        return describir("coincidencia", f"{parecido} La foto permite reconocer su forma general. Compárala con el modelo y revisa el detalle que sigue.")
    return describir("parcial", "El rasgo principal se aprecia mejor al comparar el trazo con la referencia.")
