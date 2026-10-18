"""
Paso R4 (datos reales): visor HTML para que los psicólogos califiquen cada figura (0/1).

Genera UN archivo HTML autónomo (sin internet, sin instalar nada) con, por niño y figura, la
figura MODELO al lado de la COPIA del niño. No muestra predicciones del modelo ni indicadores
(calificación a ciegas). Solo se usan los códigos NIN-xx y las hojas de figuras: la ficha de
datos personales nunca se lee. El psicólogo califica, y el visor exporta un CSV con una fila
por niño (child_id, edad_meses, F01..F15) para pasarlo luego a `cargar-calificaciones`.
"""
from __future__ import annotations

import argparse
import base64
import json
import random
import re
from pathlib import Path

import cv2

from grafomotor.config import REPO_ROOT, Config
from grafomotor.logs import obtener_logger
from grafomotor.preprocessing.hoja import normalizar_celda, segmentar_hoja

AYUDA = "datos reales: genera el visor HTML de calificación para los psicólogos"
log = obtener_logger(__name__)

# fotos que hay que repetir (niño:hoja); sus figuras se muestran marcadas y no se califican
POR_REPETIR = "NIN-11:3,NIN-55:2"
PLANTILLA = Path(__file__).with_name("visor_plantilla.html")


def agregar_argumentos(p: argparse.ArgumentParser) -> None:
    p.add_argument("--origen", default="data/hojas_reales/jpg",
                   help="carpeta con <niño>_p<N>.jpg (relativa a la raíz; también acepta ruta absoluta)")
    p.add_argument("--salida", default="data/hojas_reales/visor_calificacion.html")
    p.add_argument("--modelo-de", default="NIN-01",
                   help="niño cuyas hojas sirven para recortar las 15 figuras MODELO (impresas)")
    p.add_argument("--repetir", default=POR_REPETIR,
                   help="niño:hoja por repetir, separados por coma ('' = ninguno)")
    p.add_argument("--criterios", default=None,
                   help="JSON opcional {\"F01\": \"texto del criterio\", ...} (Apéndice C del manual)")
    p.add_argument("--orden-aleatorio", type=int, default=None, metavar="SEMILLA",
                   help="mezcla el orden de los niños (para que dos evaluadores no coincidan)")
    p.add_argument("--plantillas", default=None,
                   help="carpeta con F01.png..F15.png (por defecto, rutas.templates)")
    p.add_argument("--ancho", type=int, default=640, help="ancho en px de cada copia incrustada")
    p.add_argument("--ancho-modelo", type=int, default=900, help="ancho en px de cada figura modelo")
    p.add_argument("--solo", default=None, help="un solo niño o varios separados por coma")


def _jpg_b64(img, ancho: int, calidad: int = 78) -> str:
    f = ancho / img.shape[1]
    chico = cv2.resize(img, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", chico, [cv2.IMWRITE_JPEG_QUALITY, calidad])
    if not ok:
        raise RuntimeError("no se pudo codificar la imagen")
    return "data:image/jpeg;base64," + base64.b64encode(buf).decode()


def _hojas(origen: Path, solo: set[str] | None) -> dict[str, dict[int, Path]]:
    por_nino: dict[str, dict[int, Path]] = {}
    for foto in sorted(origen.glob("*.jpg")):
        m = re.match(r"(NIN-\d+)_p(\d)$", foto.stem)
        if m and (solo is None or m.group(1) in solo):
            por_nino.setdefault(m.group(1), {})[int(m.group(2))] = foto
    return por_nino


def _modelos(hojas: dict[int, Path], plantillas, ancho: int) -> dict[str, str]:
    """Las 15 figuras impresas, recortadas de las hojas de un niño (son iguales en todas)."""
    out: dict[str, str] = {}
    for pag, ruta in sorted(hojas.items()):
        h = segmentar_hoja(cv2.imread(str(ruta), 0), plantillas, pag)
        for i, celda in enumerate(h.modelos):
            c = normalizar_celda(celda)
            c[: int(0.14 * c.shape[0]), : int(0.12 * c.shape[1])] = 255   # borra el "2." impreso: es el n.º dentro de la hoja
            out[f"F{(h.pagina - 1) * 5 + i + 1:02d}"] = _jpg_b64(c, ancho)
    return out


def ejecutar(args: argparse.Namespace, cfg: Config) -> int:
    origen, salida = REPO_ROOT / args.origen, REPO_ROOT / args.salida
    carpeta = REPO_ROOT / args.plantillas if args.plantillas else cfg.ruta("templates")
    plantillas = {p.stem: cv2.imread(str(p), 0) for p in sorted(carpeta.glob("F*.png"))}
    repetir = {tuple(x.split(":")) for x in args.repetir.split(",") if x}
    solo = set(args.solo.split(",")) if args.solo else None
    hojas = _hojas(origen, solo)
    if not hojas:
        log.error("no hay hojas <niño>_p<N>.jpg en %s", origen)
        return 1

    fuente = _hojas(origen, {args.modelo_de}).get(args.modelo_de)
    if not fuente or len(fuente) < 3:
        log.error("el niño %s no tiene las 3 hojas para sacar las figuras modelo", args.modelo_de)
        return 1
    modelos = _modelos(fuente, plantillas, args.ancho_modelo)

    ninos = []
    for nino, paginas in hojas.items():
        figs = {}
        for pag, ruta in sorted(paginas.items()):
            try:
                h = segmentar_hoja(cv2.imread(str(ruta), 0), plantillas, pag)
            except ValueError as e:
                log.warning("%s hoja %d: %s (sus figuras no se muestran)", nino, pag, e)
                continue
            for i, celda in enumerate(h.copias):
                fid = f"F{(h.pagina - 1) * 5 + i + 1:02d}"
                repite = (nino, str(pag)) in repetir
                # una foto por repetir no se incrusta: está mal encuadrada y solo confunde
                figs[fid] = {"img": None if repite else _jpg_b64(normalizar_celda(celda), args.ancho),
                             "sale": bool(h.toca_borde[i]) and not repite,
                             "repetir": repite}
        ninos.append({"id": nino, "figuras": figs})
        log.info("%s: %d figuras", nino, len(figs))

    if args.orden_aleatorio is not None:
        random.Random(args.orden_aleatorio).shuffle(ninos)

    nombres = {fid: d["nombre"] for fid, d in cfg.raw["figuras"].items()}
    criterios = json.loads(Path(args.criterios).read_text(encoding="utf-8")) if args.criterios else {}
    datos = {"ninos": ninos, "modelos": modelos, "nombres": nombres, "criterios": criterios,
             "orden": args.orden_aleatorio}
    html = PLANTILLA.read_text(encoding="utf-8").replace("__DATOS__", json.dumps(datos))
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(html, encoding="utf-8")
    log.info("visor listo: %s (%.1f MB, %d niños)", salida, salida.stat().st_size / 1e6, len(ninos))
    return 0
