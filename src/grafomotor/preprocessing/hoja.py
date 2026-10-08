"""
Segmentación de la hoja de respuesta (Etapa 0: de la foto de la hoja a una imagen por figura).

La hoja tiene 5 figuras en una cuadrícula de 5 filas x 2 columnas (modelo a la izquierda,
copia del niño a la derecha). Se fotografía en cualquier orientación (0, 90, 180, 270 grados),
así que el paso es:

    foto -> localizar la cuadrícula -> rectificar -> poner en vertical -> decidir 0/180 grados
    comparando la columna del modelo con las plantillas -> recortar las 5 celdas de la copia

Cada paso es una función pura. Los umbrales vienen en `ParamsHoja`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

N_FILAS, N_COLS = 5, 2


@dataclass
class ParamsHoja:
    lado_trabajo_px: int = 1600        # lado mayor al localizar la cuadrícula
    bloque_adapt: int = 41             # ventana del umbral adaptativo (impar)
    c_adapt: int = 12                  # constante del umbral adaptativo
    margen_celda: float = 0.035        # fracción de la celda que se recorta junto a cada línea
    lado_huella_px: int = 48           # lado de la huella usada para comparar con la plantilla
    puntaje_min_orientacion: float = 0.25   # por debajo, la orientación se marca como dudosa
    dif_oscuridad_min: float = 10.0    # diferencia mínima modelo/copia para fiarse del giro
    rango_linea_media: tuple[float, float] = (0.25, 0.60)   # la columna del modelo es más angosta
    ventana_linea: float = 0.04        # tolerancia (fracción del alto/ancho) al buscar líneas


@dataclass
class HojaSegmentada:
    cuadricula: np.ndarray                  # gris, vertical, ya orientada
    lineas_y: list[int]                     # 6 posiciones
    lineas_x: list[int]                     # 3 posiciones
    modelos: list[np.ndarray]               # 5 celdas (gris) de la columna del modelo
    copias: list[np.ndarray]                # 5 celdas (gris) de la copia del niño
    pagina: int                             # 1, 2 o 3 (figuras 1-5, 6-10, 11-15)
    puntaje_orientacion: float
    margen_orientacion: float               # diferencia entre la mejor y la 2.ª opción
    avisos: list[str] = field(default_factory=list)
    toca_borde: list[bool] = field(default_factory=list)   # el trazo sale de la celda


# --------------------------------------------------------------------------- #
def _reducir(gris: np.ndarray, lado: int) -> tuple[np.ndarray, float]:
    f = lado / max(gris.shape)
    if f >= 1:
        return gris, 1.0
    return cv2.resize(gris, None, fx=f, fy=f, interpolation=cv2.INTER_AREA), f


def _ordenar_esquinas(pts: np.ndarray) -> np.ndarray:
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]],
                    dtype="float32")


def _cuadrilatero(contorno: np.ndarray) -> np.ndarray:
    """4 esquinas del contorno: aproximación poligonal; si no da 4, el rectángulo mínimo."""
    casco = cv2.convexHull(contorno)
    peri = cv2.arcLength(casco, True)
    for eps in (0.01, 0.015, 0.02, 0.03, 0.05):
        aprox = cv2.approxPolyDP(casco, eps * peri, True)
        if len(aprox) == 4:
            return aprox.reshape(4, 2).astype("float32")
    return cv2.boxPoints(cv2.minAreaRect(casco)).astype("float32")


def localizar_cuadricula(gris: np.ndarray, p: ParamsHoja) -> np.ndarray | None:
    """Esquinas (en coordenadas de `gris`) del borde exterior de la cuadrícula impresa."""
    chica, f = _reducir(gris, p.lado_trabajo_px)
    suave = cv2.GaussianBlur(chica, (5, 5), 0)
    b = cv2.adaptiveThreshold(suave, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV,
                              p.bloque_adapt, p.c_adapt)
    b = cv2.morphologyEx(b, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(b, connectivity=8)
    if n <= 1:
        return None
    alto, ancho = chica.shape
    mejor, mejor_area = None, 0
    for i in range(1, n):
        w, h, area = st[i, cv2.CC_STAT_WIDTH], st[i, cv2.CC_STAT_HEIGHT], st[i, cv2.CC_STAT_AREA]
        if w * h < 0.15 * alto * ancho:
            continue
        # la cuadrícula es una línea fina: ocupa poco de su caja (descarta bordes de mesa/hoja)
        relleno = area / float(w * h)
        if relleno > 0.25:
            continue
        # marco de la foto o sombra del borde, no la tabla
        if w > 0.97 * ancho and h > 0.97 * alto:
            continue
        if w * h > mejor_area:
            mejor, mejor_area = i, w * h
    if mejor is None:
        return None
    cont, _ = cv2.findContours((lab == mejor).astype(np.uint8), cv2.RETR_EXTERNAL,
                               cv2.CHAIN_APPROX_SIMPLE)
    c = max(cont, key=cv2.contourArea)
    return _cuadrilatero(c) / f


def rectificar(gris: np.ndarray, esquinas: np.ndarray) -> np.ndarray:
    src = _ordenar_esquinas(esquinas)
    w = int(max(np.linalg.norm(src[0] - src[1]), np.linalg.norm(src[2] - src[3])))
    h = int(max(np.linalg.norm(src[0] - src[3]), np.linalg.norm(src[1] - src[2])))
    dst = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype="float32")
    M = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(gris, M, (w, h), flags=cv2.INTER_CUBIC,
                               borderMode=cv2.BORDER_REPLICATE)


def _poner_vertical(gris: np.ndarray) -> np.ndarray:
    return cv2.rotate(gris, cv2.ROTATE_90_CLOCKWISE) if gris.shape[1] > gris.shape[0] else gris


# --------------------------------------------------------------------------- #
def _lineas(gris: np.ndarray, p: ParamsHoja, horizontal: bool,
            n_esperadas: int) -> tuple[list[int], int]:
    """Posiciones de las líneas de la cuadrícula; si no se hallan, reparto uniforme."""
    h, w = gris.shape
    b = cv2.adaptiveThreshold(cv2.GaussianBlur(gris, (5, 5), 0), 255,
                              cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV,
                              p.bloque_adapt, p.c_adapt)
    largo = int((w if horizontal else h) * 0.18)
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (largo, 1) if horizontal else (1, largo))
    m = cv2.morphologyEx(b, cv2.MORPH_OPEN, k)
    proy = m.sum(axis=1 if horizontal else 0).astype(float)
    n = h if horizontal else w
    uniforme = [round(i * (n - 1) / n_esperadas) for i in range(n_esperadas + 1)]
    if proy.max() <= 0:
        return uniforme, 0
    proy = np.convolve(proy, np.ones(5) / 5, mode="same")
    ventana = max(3, int(n * p.ventana_linea))
    elegidas, halladas = [], 0
    # el pico más fuerte cerca de cada posición esperada
    for k, objetivo in enumerate(uniforme):
        lo, hi = max(0, objetivo - ventana), min(n, objetivo + ventana + 1)
        if not horizontal and k == 1:             # línea entre modelo y copia: no está en el centro
            lo, hi = int(p.rango_linea_media[0] * n), int(p.rango_linea_media[1] * n)
        j = lo + int(np.argmax(proy[lo:hi]))
        ok = proy[j] > 0.25 * proy.max()
        halladas += int(ok and 0 < len(elegidas) < n_esperadas)   # solo líneas interiores
        elegidas.append(j if ok else objetivo)
    return elegidas, halladas


def _celdas(gris: np.ndarray, ys: list[int], xs: list[int], col: int, margen: float):
    out = []
    for i in range(N_FILAS):
        y0, y1, x0, x1 = ys[i], ys[i + 1], xs[col], xs[col + 1]
        my, mx = int((y1 - y0) * margen) + 3, int((x1 - x0) * margen) + 3
        out.append(gris[y0 + my: y1 - my, x0 + mx: x1 - mx].copy())
    return out


# --------------------------------------------------------------------------- #
def _fondo(celda: np.ndarray) -> np.ndarray:
    """Luz de fondo de la celda (rápida: se estima a 1/8 de tamaño y se vuelve a ampliar)."""
    h, w = celda.shape
    chica = cv2.resize(celda, (max(2, w // 8), max(2, h // 8)), interpolation=cv2.INTER_AREA)
    chica = cv2.GaussianBlur(cv2.dilate(chica, np.ones((5, 5), np.uint8)), (0, 0), 3)
    return cv2.resize(chica, (w, h), interpolation=cv2.INTER_LINEAR)


def _tinta(celda: np.ndarray) -> np.ndarray:
    """Máscara binaria (255 = tinta) de una celda, sin fondo ni número de la esquina."""
    suave = cv2.GaussianBlur(celda, (3, 3), 0)
    norm = cv2.divide(suave, _fondo(celda), scale=255)
    _, b = cv2.threshold(norm, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    h, w = b.shape
    n, lab, st, _ = cv2.connectedComponentsWithStats(b, connectivity=8)
    for i in range(1, n):
        x, y, cw, ch, area = st[i]
        pequeno = area < 0.002 * h * w
        en_esquina = x + cw < 0.28 * w and y + ch < 0.30 * h
        # resto de la línea de la cuadrícula: delgada, larga y pegada al borde de la celda
        toca = x <= 1 or y <= 1 or x + cw >= w - 1 or y + ch >= h - 1
        es_linea = toca and min(cw, ch) < 0.03 * max(h, w) and max(cw, ch) > 0.6 * min(h, w)
        if pequeno or en_esquina or es_linea:
            b[lab == i] = 0
    return b


def huella(binaria: np.ndarray, lado: int = 48) -> np.ndarray | None:
    """Recorta al trazo, centra en un cuadrado y engrosa: comparable entre modelo y plantilla."""
    ys, xs = np.where(binaria > 0)
    if len(xs) < 20:
        return None
    r = binaria[ys.min(): ys.max() + 1, xs.min(): xs.max() + 1]
    h, w = r.shape
    s = max(h, w)
    cuadro = np.zeros((s, s), np.uint8)
    cuadro[(s - h) // 2:(s - h) // 2 + h, (s - w) // 2:(s - w) // 2 + w] = r
    ch = cv2.resize(cuadro, (lado, lado), interpolation=cv2.INTER_AREA)
    ch = (ch > 40).astype(np.uint8)
    return cv2.dilate(ch, np.ones((3, 3), np.uint8))


def _sin_marco(plantilla: np.ndarray, grosor: int = 6) -> np.ndarray:
    """Las plantillas traen restos en el borde del lienzo: se borran antes de comparar."""
    t = plantilla.copy()
    t[:grosor], t[-grosor:], t[:, :grosor], t[:, -grosor:] = 0, 0, 0, 0
    return t


def _dice(a: np.ndarray | None, b: np.ndarray | None) -> float:
    if a is None or b is None:
        return 0.0
    inter = float((a & b).sum())
    return 2 * inter / max(float(a.sum() + b.sum()), 1.0)


def _oscuridad_trazo(celdas: list[np.ndarray]) -> float | None:
    """Gris típico (percentil 25, 0 = negro) del trazo de una columna de celdas."""
    vals = []
    for c in celdas:
        b = _tinta(c) > 0
        if b.sum() < 30:
            continue
        norm = cv2.divide(cv2.GaussianBlur(c, (3, 3), 0), _fondo(c), scale=255)
        vals.append(np.percentile(norm[b], 25))
    return float(np.mean(vals)) if vals else None


def orientacion_por_trazo(vertical: np.ndarray, ys: list[int], xs: list[int], p: ParamsHoja):
    """0 o 180 grados según qué columna tiene el trazo más oscuro: el modelo está impreso
    (negro, ~60 de 255) y la copia es lápiz (gris, ~130). Devuelve (giro, diferencia)."""
    izq = _oscuridad_trazo(_celdas(vertical, ys, xs, 0, p.margen_celda))
    der = _oscuridad_trazo(_celdas(vertical, ys, xs, 1, p.margen_celda))
    if izq is None or der is None:
        return 0, 0.0
    return (0 if izq < der else 180), abs(der - izq)


def decidir_orientacion(vertical: np.ndarray, plantillas: dict[str, np.ndarray], p: ParamsHoja,
                        ys: list[int], xs: list[int], pagina: int | None = None):
    """Prueba 0 y 180 grados y las 3 páginas; devuelve (giro, pagina, puntaje, margen, todos)."""
    hp = {k: huella(_sin_marco(v), p.lado_huella_px) for k, v in plantillas.items()}
    ids = sorted(hp)
    puntajes = {}
    for giro in (0, 180):
        g = vertical if giro == 0 else cv2.rotate(vertical, cv2.ROTATE_180)
        yy = ys if giro == 0 else [g.shape[0] - 1 - y for y in ys[::-1]]
        xx = xs if giro == 0 else [g.shape[1] - 1 - x for x in xs[::-1]]
        modelos = _celdas(g, yy, xx, 0, p.margen_celda)
        hm = [huella(_tinta(c), p.lado_huella_px) for c in modelos]
        for pag in ((pagina,) if pagina else (1, 2, 3)):
            fig = [ids[(pag - 1) * N_FILAS + i] for i in range(N_FILAS)]
            dados = [_dice(hm[i], hp[fig[i]]) for i in range(N_FILAS)]
            puntajes[(giro, pag)] = float(np.mean(dados))
    orden = sorted(puntajes.items(), key=lambda kv: -kv[1])
    (giro, pag), mejor = orden[0]
    return giro, pag, mejor, mejor - orden[1][1], puntajes


# --------------------------------------------------------------------------- #
def segmentar_hoja(gris: np.ndarray, plantillas: dict[str, np.ndarray],
                   pagina_esperada: int | None = None,
                   p: ParamsHoja | None = None) -> HojaSegmentada:
    p = p or ParamsHoja()
    avisos: list[str] = []
    esq = localizar_cuadricula(gris, p)
    if esq is None:
        raise ValueError("no se encontró la cuadrícula de la hoja")
    vertical = _poner_vertical(rectificar(gris, esq))
    ys, _ = _lineas(vertical, p, True, N_FILAS)
    xs, _ = _lineas(vertical, p, False, N_COLS)

    # la página sale del orden de las fotos (1.ª, 2.ª, 3.ª hoja); las plantillas solo deciden 0/180
    giro, pag, punt, margen, _ = decidir_orientacion(
        vertical, plantillas, p, ys, xs, pagina_esperada)
    giro_trazo, dif = orientacion_por_trazo(vertical, ys, xs, p)
    if giro_trazo != giro and margen > 0.1:
        avisos.append("la orientación por trazo y por plantilla no coinciden")
    giro = giro_trazo                            # el trazo es la señal más fiable (60 de 60)
    if dif < p.dif_oscuridad_min:
        avisos.append(f"orientación dudosa (diferencia de oscuridad {dif:.0f})")
    if giro == 180:
        vertical = cv2.rotate(vertical, cv2.ROTATE_180)
        ys, _ = _lineas(vertical, p, True, N_FILAS)
        xs, _ = _lineas(vertical, p, False, N_COLS)
    ys_ok, xs_ok = _lineas(vertical, p, True, N_FILAS)[1], _lineas(vertical, p, False, N_COLS)[1]
    if ys_ok + xs_ok < 3:
        avisos.append(f"cuadrícula mal ajustada ({ys_ok + xs_ok} de 5 líneas interiores halladas)")
    if pagina_esperada is not None and pag != pagina_esperada:
        avisos.append(f"la hoja parece la página {pag}, no la {pagina_esperada}")

    modelos = _celdas(vertical, ys, xs, 0, p.margen_celda)
    copias = _celdas(vertical, ys, xs, 1, p.margen_celda)
    toca = []
    for c in copias:
        b = _tinta(c)
        franja = np.concatenate([b[:3].ravel(), b[-3:].ravel(),
                                 b[:, :3].ravel(), b[:, -3:].ravel()])
        toca.append(bool((franja > 0).mean() > 0.02))
    return HojaSegmentada(vertical, ys, xs, modelos, copias, pag, punt, margen, avisos, toca)


def normalizar_celda(celda: np.ndarray) -> np.ndarray:
    """Quita el gradiente de luz de la celda: fondo blanco y trazo gris/negro."""
    return cv2.divide(cv2.GaussianBlur(celda, (3, 3), 0), _fondo(celda), scale=255)
