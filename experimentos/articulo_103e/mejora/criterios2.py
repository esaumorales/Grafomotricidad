"""Indicadores adicionales por criterio del manual (Apéndice C), pensados para las figuras en que
el modelo falla (F02, F05, F11, F13, F14, F15). Se miden sobre la figura binaria registrada
(trazo blanco sobre negro, 512 px), igual que criterios.py, y también en la plantilla.

  huecos         ¿cuántas zonas cerradas forma el trazo?      (figura cerrada = 1; dos figuras
                                                                tangentes = 2; secantes = 3;
                                                                curvas tangentes sin superponer = 0)
  hueco_mayor    área de la zona cerrada mayor / área del dibujo
  redondez       4πA/P² de la zona cerrada mayor               (círculo ≈ 1; cuadrado ≈ 0.79)
  vertices_hueco vértices del polígono de la zona cerrada mayor
  error_recto    desvío medio de sus ángulos frente a 90°     (ángulos "aproximadamente rectos")
  rectitud       cuerda / largo de las ramas largas del esqueleto (recta = 1; curva < 1)
  rectitud_min   la rama menos recta                           ("ninguna línea es curva")
  tinta_arriba   fracción del trazo en la mitad superior       (qué figura va arriba)
  tinta_derecha  fracción del trazo en la mitad derecha
  redondez_arriba / redondez_abajo  redondez de la zona cerrada mayor de cada mitad
                                     (círculo arriba y triángulo abajo, o al revés)

Los parámetros se fijaron a partir del manual antes de ver resultados."""
from __future__ import annotations

import cv2
import numpy as np
from skimage.morphology import skeletonize

from criterios import CIERRE_PX, HUECO_MIN_PX, SUAVE_SIGMA, _podar, _vecinos

HUECO_FIGURA_PX = 1500     # una zona cerrada menor que esto no se cuenta como hueco de la figura
RAMA_MIN_PX = 40           # ramas del esqueleto más cortas no se usan para la rectitud
EPS_POLIGONO = 0.03        # tolerancia de Douglas-Peucker (fracción del perímetro)

CLAVES = ["huecos", "hueco_mayor", "redondez", "vertices_hueco", "error_recto", "rectitud",
          "rectitud_min", "tinta_arriba", "tinta_derecha", "redondez_arriba", "redondez_abajo"]


def _liso(b: np.ndarray) -> np.ndarray:
    borroso = cv2.GaussianBlur(b.astype(np.float32), (0, 0), SUAVE_SIGMA)
    liso = (borroso > 0.25).astype(np.uint8)
    liso = cv2.morphologyEx(liso, cv2.MORPH_CLOSE, np.ones((CIERRE_PX, CIERRE_PX), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats((1 - liso).astype(np.uint8), connectivity=4)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < HUECO_MIN_PX:
            liso[lab == i] = 1
    return liso


def _huecos(liso: np.ndarray) -> list[np.ndarray]:
    """Zonas de fondo encerradas por el trazo (no tocan el borde del lienzo), de mayor a menor."""
    n, lab, st, _ = cv2.connectedComponentsWithStats((1 - liso).astype(np.uint8), connectivity=4)
    h, w = liso.shape
    out = []
    for i in range(1, n):
        x, y, ww, hh, a = st[i]
        if a < HUECO_FIGURA_PX or x == 0 or y == 0 or x + ww >= w or y + hh >= h:
            continue
        out.append(lab == i)
    return sorted(out, key=lambda m: -m.sum())


def _redondez(m: np.ndarray) -> float:
    cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cs:
        return np.nan
    c = max(cs, key=cv2.contourArea)
    p = cv2.arcLength(c, True)
    return float(4 * np.pi * cv2.contourArea(c) / p ** 2) if p > 0 else np.nan


def _poligono(m: np.ndarray) -> tuple[int, float]:
    cs, _ = cv2.findContours(m.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not cs:
        return 0, np.nan
    c = max(cs, key=cv2.contourArea)
    ap = cv2.approxPolyDP(c, EPS_POLIGONO * cv2.arcLength(c, True), True).reshape(-1, 2).astype(float)
    k = len(ap)
    if k < 3:
        return k, np.nan
    angs = []
    for i in range(k):
        a, b, c2 = ap[i - 1], ap[i], ap[(i + 1) % k]
        v1, v2 = a - b, c2 - b
        cos = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-9)
        angs.append(np.degrees(np.arccos(np.clip(cos, -1, 1))))
    return k, float(np.mean(np.abs(np.array(angs) - 90)))


def _largo(r: np.ndarray) -> float:
    """Largo de una línea de un píxel: pasos horizontales/verticales valen 1 y los diagonales
    (que no forman esquina con un paso recto) valen raíz de 2."""
    r = r.astype(np.uint8)
    h = (r[:, 1:] & r[:, :-1]).sum() + (r[1:, :] & r[:-1, :]).sum()
    d1 = r[1:, 1:] & r[:-1, :-1] & ~(r[1:, :-1] | r[:-1, 1:]) & 1
    d2 = r[1:, :-1] & r[:-1, 1:] & ~(r[1:, 1:] | r[:-1, :-1]) & 1
    return float(h + np.sqrt(2) * (d1.sum() + d2.sum()))


def _rectitud(liso: np.ndarray) -> tuple[float, float]:
    """Rectitud de las ramas del esqueleto: se cortan en los nodos (3+ vecinos) y cada rama
    larga se compara con la recta entre sus extremos."""
    esq = _podar(skeletonize(liso.astype(bool)))
    v = _vecinos(esq)
    ramas = esq & ~cv2.dilate(((v >= 3) & esq).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    n, lab, st, _ = cv2.connectedComponentsWithStats(ramas.astype(np.uint8), connectivity=8)
    vals = []
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] < RAMA_MIN_PX:
            continue
        r = lab == i
        largo = _largo(r)
        ys, xs = np.nonzero(r)
        pts = np.stack([xs, ys], 1).astype(float)
        # extremos aproximados: los dos puntos más alejados entre sí sobre el eje principal
        c = pts - pts.mean(0)
        eje = np.linalg.svd(c, full_matrices=False)[2][0]
        proy = c @ eje
        cuerda = float(np.linalg.norm(pts[np.argmax(proy)] - pts[np.argmin(proy)]))
        vals.append(min(1.0, cuerda / largo))
    if not vals:
        return np.nan, np.nan
    return float(np.mean(vals)), float(np.min(vals))


def medir2(binaria: np.ndarray) -> dict:
    b = binaria > 0
    if b.sum() < 20:
        return {k: np.nan for k in CLAVES}
    liso = _liso(b)
    hs = _huecos(liso)
    ys, xs = np.nonzero(b)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    area = max(1, (y1 - y0 + 1) * (x1 - x0 + 1))
    my, mx = (y0 + y1) / 2, (x0 + x1) / 2
    vert, err = _poligono(hs[0]) if hs else (0, np.nan)
    rect, rect_min = _rectitud(liso)

    def red_mitad(arriba: bool) -> float:
        sel = [h for h in hs if (np.nonzero(h)[0].mean() < my) == arriba]
        return _redondez(sel[0]) if sel else np.nan

    return {"huecos": len(hs), "hueco_mayor": float(hs[0].sum() / area) if hs else 0.0,
            "redondez": _redondez(hs[0]) if hs else np.nan, "vertices_hueco": vert,
            "error_recto": err, "rectitud": rect, "rectitud_min": rect_min,
            "tinta_arriba": float((ys < my).mean()), "tinta_derecha": float((xs > mx).mean()),
            "redondez_arriba": red_mitad(True), "redondez_abajo": red_mitad(False)}
