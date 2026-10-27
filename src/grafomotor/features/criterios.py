"""Indicadores por criterio del manual (Apéndice C), medidos sobre la figura binaria registrada
(trazo blanco sobre negro, 512 px). Cada uno responde una pregunta que hace el evaluador:

  partes         ¿cuántos trazos separados hay?          (una línea, dos líneas, ondas separadas)
  partes_juntas  ¿cuántos trazos sin unir huecos?         (si dos partes se tocan o no)
  dist_partes    ¿qué tan lejos están las dos partes mayores? (tangencia, sin contacto)
  extremos       ¿cuántas puntas libres tiene el trazo?   (líneas abiertas, figura cerrada = 0)
  cruces         ¿cuántos puntos donde se juntan 3+ ramas? (cruce, convergencia, superposición)
  ondas          ¿cuántas subidas y bajadas tiene el trazo principal? (nº de ondulaciones)
  esquinas       ¿cuántos giros bruscos (> 60°) tiene?   (ángulos donde va curva y al revés)
  giro_max       ¿qué tan brusco es el giro más fuerte?  (pico frente a curva suave)
  inclinacion    ¿cuánto se inclina el dibujo frente al modelo? (regla de los 45°)
  incl_partes    inclinación mayor de las dos partes principales frente a la horizontal

Los parámetros se fijaron antes de ver resultados y no se ajustan mirando las métricas.
Para cada figura se mide lo mismo en la plantilla del modelo, y el modelo recibe el valor del
niño y la diferencia con el modelo (dif_*)."""
from __future__ import annotations

from collections import deque

import cv2
import numpy as np
from skimage.morphology import skeletonize

FRACCION_MIN = 0.05   # igual que preprocesamiento.fraccion_min_trazo
UNION_PX = 9          # une huecos pequeños del lápiz antes de contar partes
PODA_PX = 12          # ramitas del esqueleto más cortas que esto se ignoran
SUAVIZADO = 15        # ventana (en puntos) para suavizar el trazo antes de medir giros
PASO_GIRO = 12        # distancia (en puntos) para medir el ángulo de giro
GIRO_ESQUINA = 60.0   # grados: un giro mayor es una esquina
PROMINENCIA = 0.04    # fracción del lado (512 px) para contar una subida/bajada como onda
SUAVE_SIGMA = 3.0     # desenfoque del trazo antes del esqueleto (alisa el borde del lápiz)
CIERRE_PX = 7        # cierre morfológico del trazo antes del esqueleto
HUECO_MIN_PX = 300    # agujeros más chicos que esto se rellenan (no son huecos de la figura)

VECINOS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def _componentes(b: np.ndarray, unir: bool) -> list[np.ndarray]:
    m = b.astype(np.uint8)
    if unir:
        m = cv2.dilate(m, np.ones((UNION_PX, UNION_PX), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    if n <= 1:
        return []
    areas = st[1:, cv2.CC_STAT_AREA]
    orden = np.argsort(-areas)
    return [(lab == i + 1) & b for i in orden if areas[i] >= FRACCION_MIN * areas.max()]


def _vecinos(esq: np.ndarray) -> np.ndarray:
    k = np.ones((3, 3), np.uint8); k[1, 1] = 0
    return cv2.filter2D(esq.astype(np.uint8), -1, k, borderType=cv2.BORDER_CONSTANT) * esq


def _podar(esq: np.ndarray) -> np.ndarray:
    """Quita ramitas cortas borrando extremos PODA_PX veces (las líneas largas solo se acortan)."""
    e = esq.copy()
    for _ in range(PODA_PX):
        v = _vecinos(e)
        e = e & ~((v <= 1) & e)
    return e


def _camino_mas_largo(esq: np.ndarray) -> np.ndarray:
    pts = np.argwhere(esq)
    if len(pts) < 2:
        return pts
    idx = {tuple(p): i for i, p in enumerate(pts)}

    def bfs(i0):
        prev = np.full(len(pts), -1); dist = np.full(len(pts), -1); dist[i0] = 0
        q = deque([i0])
        while q:
            i = q.popleft(); y, x = pts[i]
            for dy, dx in VECINOS:
                j = idx.get((y + dy, x + dx))
                if j is not None and dist[j] < 0:
                    dist[j] = dist[i] + 1; prev[j] = i; q.append(j)
        return int(np.argmax(dist)), prev

    a, _ = bfs(0)
    b, prev = bfs(a)
    camino = [b]
    while prev[camino[-1]] >= 0:
        camino.append(prev[camino[-1]])
    return pts[camino]


def _angulo_pca(m: np.ndarray) -> float:
    ys, xs = np.nonzero(m)
    if len(xs) < 5:
        return np.nan
    c = np.cov(np.vstack([xs, ys]))
    w, v = np.linalg.eigh(c)
    vx, vy = v[:, np.argmax(w)]
    return float(np.degrees(np.arctan2(vy, vx)) % 180)


def _dif_angular(a: float, b: float) -> float:
    if np.isnan(a) or np.isnan(b):
        return np.nan
    d = abs(a - b) % 180
    return min(d, 180 - d)


def medir(binaria: np.ndarray) -> dict:
    b = binaria > 0
    if b.sum() < 20:
        return {k: np.nan for k in ("partes", "partes_juntas", "dist_partes", "extremos", "cruces",
                                     "ondas", "esquinas", "giro_max", "angulo", "incl_partes")}
    partes = _componentes(b, unir=True)
    juntas = _componentes(b, unir=False)
    if len(partes) >= 2:
        dt = cv2.distanceTransform((~partes[0]).astype(np.uint8), cv2.DIST_L2, 3)
        dist = float(dt[partes[1]].min())
    else:
        dist = 0.0
    # el trazo de lápiz tiene huecos y bordes rugosos que llenan el esqueleto de anillos falsos:
    # se cierra el trazo y se rellenan los agujeros pequeños antes de adelgazarlo
    borroso = cv2.GaussianBlur(b.astype(np.float32), (0, 0), SUAVE_SIGMA)
    liso = (borroso > 0.25).astype(np.uint8)
    liso = cv2.morphologyEx(liso, cv2.MORPH_CLOSE, np.ones((CIERRE_PX, CIERRE_PX), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats((1 - liso).astype(np.uint8), connectivity=4)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < HUECO_MIN_PX:
            liso[lab == i] = 1
    esq_completo = skeletonize(liso.astype(bool))
    esq = _podar(esq_completo)
    v = _vecinos(esq)
    extremos = int(((v == 1) & esq).sum())
    nodos = ((v >= 3) & esq).astype(np.uint8)
    cruces = int(cv2.connectedComponents(cv2.dilate(nodos, np.ones((5, 5), np.uint8)))[0] - 1)

    # trazo principal: camino más largo del esqueleto de la parte mayor
    principal = esq_completo & cv2.dilate(partes[0].astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    cam = _camino_mas_largo(principal).astype(float)
    ondas = esquinas = 0
    giro_max = 0.0
    if len(cam) > 2 * SUAVIZADO:
        k = np.ones(SUAVIZADO) / SUAVIZADO
        ys = np.convolve(cam[:, 0], k, mode="valid"); xs = np.convolve(cam[:, 1], k, mode="valid")
        # ondas: cambios de subida a bajada (y al revés) mayores que el umbral (zigzag)
        umbral = PROMINENCIA * binaria.shape[0]
        direccion, ref = 0, ys[0]
        for y in ys[1:]:
            if direccion == 0:
                if abs(y - ref) > umbral:
                    direccion, ref = (1 if y > ref else -1), y
            elif direccion * (y - ref) > 0:
                ref = y
            elif abs(y - ref) > umbral:
                direccion, ref, ondas = -direccion, y, ondas + 1
        # giros
        if len(xs) > 2 * PASO_GIRO:
            d1 = np.stack([xs[PASO_GIRO:-PASO_GIRO] - xs[:-2 * PASO_GIRO], ys[PASO_GIRO:-PASO_GIRO] - ys[:-2 * PASO_GIRO]], 1)
            d2 = np.stack([xs[2 * PASO_GIRO:] - xs[PASO_GIRO:-PASO_GIRO], ys[2 * PASO_GIRO:] - ys[PASO_GIRO:-PASO_GIRO]], 1)
            cos = (d1 * d2).sum(1) / (np.linalg.norm(d1, axis=1) * np.linalg.norm(d2, axis=1) + 1e-9)
            giro = np.degrees(np.arccos(np.clip(cos, -1, 1)))
            giro_max = float(giro.max())
            fuerte = giro > GIRO_ESQUINA
            esquinas = int(np.sum(fuerte[1:] & ~fuerte[:-1]) + fuerte[0])
    angs = [_angulo_pca(p) for p in partes[:2]]
    incl = [min(a, 180 - a) for a in angs if not np.isnan(a)]   # 0 = horizontal, 90 = vertical
    return {"partes": len(partes), "partes_juntas": len(juntas), "dist_partes": dist,
            "extremos": extremos, "cruces": cruces, "ondas": int(ondas), "esquinas": esquinas,
            "giro_max": giro_max, "angulo": _angulo_pca(b),
            "incl_partes": float(max(incl)) if incl else np.nan}
