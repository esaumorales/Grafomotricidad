"""
Orquestador de inferencia: junta todas las etapas para una sesión (un niño).

foto(s) -> preprocesar -> extraer indicadores -> modelo (puntaje por figura) ->
scoring (PD -> T -> nivel) -> SHAP -> explicación en lenguaje natural -> se guarda
en SQLite (data/app.db) para que el Dashboard Docente tenga historial real.

Modelo: Random Forest final 103h, cargado desde models/real/actual con config_real.yaml.
Las plantillas y el baremo se leen de las rutas indicadas por la configuración.
"""
from __future__ import annotations

from itertools import permutations
from pathlib import Path

import cv2
import numpy as np

from grafomotor import ORDEN
from grafomotor.artefactos import Artefactos
from grafomotor.config import load_config
from grafomotor.explain import construir_informe, explicar_para_docente, shap_por_sesion
from grafomotor.features.extract import extraer_indicadores
from grafomotor.io import a_binaria, cargar_plantillas, leer_gris, ruta_plantilla
from grafomotor.model.final_103h import ModeloFinal
from grafomotor.model.predict import PrediccionFigura, agregar_sesion
from grafomotor.preprocessing import preprocesar_figura
from grafomotor.preprocessing.hoja import normalizar_celda, segmentar_hoja
from grafomotor.scoring.baremo import cargar_baremo, pd_a_percentil
from grafomotor.scoring.niveles import CriterioNiveles, NivelResultado
from grafomotor.webapp import db


PAGINAS = (1, 2, 3)


def asignar_paginas(puntajes: list[dict[int, float]], tolerancia: float = 0.05) -> list[int]:
    """Página (1, 2 o 3) de cada foto, sin repetir ninguna.

    `puntajes[i]` es el parecido de la foto i con cada página. Con 3 fotos se prueban los 6 repartos
    posibles y gana el de mayor parecido total. Si el orden en que la docente puso las fotos
    (Foto 1 = figuras 1-5, Foto 2 = 6-10, Foto 3 = 11-15) queda a menos de `tolerancia` del mejor,
    se respeta ese orden: así una foto dudosa no se confunde con otra hoja. Con otra cantidad de
    fotos, cada una toma su página más parecida (y luego se avisa si faltan o se repiten)."""
    elegidas = [max(p, key=p.get) if p else None for p in puntajes]
    if len(puntajes) != len(PAGINAS) or not all(puntajes):
        return elegidas

    def total(reparto: tuple[int, ...]) -> float:
        return sum(puntajes[i].get(pag, 0.0) for i, pag in enumerate(reparto))

    mejor = max(permutations(PAGINAS), key=total)
    if total(PAGINAS) >= total(mejor) - tolerancia:
        return list(PAGINAS)
    return list(mejor)


def _leer_gris(contenido: bytes) -> np.ndarray | None:
    """Foto (JPG, PNG, HEIC del iPhone...) -> gris, respetando la orientación del celular. None si no se abre."""
    gris = cv2.imdecode(np.frombuffer(contenido, np.uint8), cv2.IMREAD_GRAYSCALE)
    if gris is not None:
        return gris
    try:
        import io

        from PIL import Image, ImageOps
        from pillow_heif import register_heif_opener

        register_heif_opener()
        with Image.open(io.BytesIO(contenido)) as im:
            return np.asarray(ImageOps.exif_transpose(im).convert("L"))
    except Exception:
        return None


class ErrorHoja(ValueError):
    """Una foto de hoja no se pudo usar; el mensaje está escrito para el docente."""


class Servicio:
    """Carga modelo + baremo + plantillas una sola vez y sirve evaluaciones."""

    def __init__(self, config_path: str | None = None):
        self.cfg = load_config(config_path)
        carpeta_modelo = Artefactos.de_config(self.cfg).dir_modelo_ml
        self.final = ModeloFinal(carpeta_modelo)
        self.modelo = self.final.modelo
        self.manifiesto = {
            **self.final.manifiesto,
            "git_hash": self.final.manifiesto.get("version", ""),
            "version_baremo": str(self.cfg.get("scoring", "version_baremo", default="")),
        }
        self.plantillas = cargar_plantillas(self.cfg, estricto=False)
        self.figuras_meta = self.cfg.figuras
        # Si el modelo trae sus propias plantillas y medidas esperadas (scripts/instalar_modelo_final.py),
        # se usan para medir los dibujos: son las del entrenamiento. Con las de config/ las medidas
        # cambian y ~1 de cada 9 figuras recibía otra nota que la del modelo del artículo.
        propias = carpeta_modelo / "plantillas"
        for fid in self.final.figuras:
            if (propias / f"{fid}.png").exists():
                self.plantillas[fid] = a_binaria(leer_gris(propias / f"{fid}.png"))
        meta_modelo = self.final.manifiesto.get("figuras_meta") or {}
        self.figuras_meta = {fid: {**m, **meta_modelo.get(fid, {})} for fid, m in self.cfg.figuras.items()}
        # columnas con que se entrenó el modelo cargado (los modelos antiguos solo tienen las 6)
        self.nombres = list(self.manifiesto.get("feature_names") or ORDEN)
        self.baremo = cargar_baremo(self.cfg.ruta("baremos"))
        self.exp_cfg = self.cfg.get("explicacion", default={})
        self.sco_cfg = self.cfg.get("scoring", default={})
        self.criterio = CriterioNiveles.de_config(self.cfg)
        self.db_path = self.cfg.ruta("db")
        db.iniciar_db(self.db_path)

    def ruta_plantilla(self, figura_id: str) -> Path | None:
        propia = Artefactos.de_config(self.cfg).dir_modelo_ml / "plantillas" / f"{figura_id}.png"
        p = propia if propia.exists() else ruta_plantilla(self.cfg, figura_id)
        return p if p.exists() else None

    def _nivel(self, pd_total: int, edad_meses: int) -> tuple[dict, NivelResultado]:
        """PD -> (tramo, percentil) -> nivel, con el criterio de config.yaml."""
        tPc = pd_a_percentil(pd_total, edad_meses, self.baremo)
        return tPc, self.criterio.clasificar(pd_total, edad_meses, self.baremo)

    def guardar_foto(self, child_id: str, figura_id: str, contenido: bytes, sufijo: str) -> Path:
        """Guarda la foto subida en data/raw/<child_id>/<figura_id>.<sufijo> (persistente,
        a diferencia de un directorio temporal) para poder mostrarla luego en 'Comparar figura'."""
        carpeta = self.cfg.ruta("raw") / child_id
        carpeta.mkdir(parents=True, exist_ok=True)
        destino = carpeta / f"{figura_id}{sufijo}"
        destino.write_bytes(contenido)
        return destino

    def ruta_foto(self, child_id: str, figura_id: str) -> Path | None:
        carpeta = self.cfg.ruta("raw") / child_id
        if not carpeta.exists():
            return None
        coincidencias = list(carpeta.glob(f"{figura_id}.*"))
        return coincidencias[0] if coincidencias else None

    # ------------------------------------------------------------------ #
    def _plantillas_gris(self) -> dict[str, np.ndarray]:
        """Plantillas en gris (como las lee el detector de hojas para comparar la columna del modelo)."""
        if getattr(self, "_gris", None) is None:
            self._gris = {}
            for fid in sorted(self.plantillas):
                ruta = self.ruta_plantilla(fid)
                if ruta is not None:
                    self._gris[fid] = cv2.imread(str(ruta), cv2.IMREAD_GRAYSCALE)
        return self._gris

    def recortar_hojas(self, child_id: str, hojas: list[tuple[str, bytes]]) -> tuple[dict[str, Path], list[str]]:
        """Fotos de las hojas -> una imagen por figura (las 5 celdas de la copia de cada hoja).

        Las hojas pueden venir en cualquier orden y giradas: la página (1.ª a 3.ª) se reconoce
        comparando la columna del modelo con las plantillas. Se necesitan las 3 hojas.
        Devuelve ({figura_id: ruta de la imagen recortada}, avisos para el panel técnico)."""
        ids = sorted(self.plantillas)
        plantillas = self._plantillas_gris()
        por_pagina: dict[int, tuple[str, object]] = {}
        avisos: list[str] = []
        segmentadas = []
        for numero, (nombre, contenido) in enumerate(hojas, start=1):
            etiqueta = f"Foto {numero} («{nombre}»)"
            gris = _leer_gris(contenido)
            if gris is None:
                raise ErrorHoja(f"No se pudo abrir la {etiqueta}. Sube una foto (JPG o PNG).")
            try:
                h = segmentar_hoja(gris, plantillas, None, imagen_completa_si_falla=True)
            except ValueError:
                raise ErrorHoja(
                    f"No se encontró la hoja en la {etiqueta}. Toma la foto con toda la hoja a la vista, "
                    "sobre una mesa lisa y con buena luz.") from None
            segmentadas.append((etiqueta, h))
        # cada foto recibe una página distinta (si una foto es dudosa, decide el orden en que se subió)
        puntajes = [getattr(h, "puntajes_pagina", None) or {h.pagina: 1.0} for _, h in segmentadas]
        asignadas = asignar_paginas(puntajes)
        for (etiqueta, h), pag in zip(segmentadas, asignadas):
            if pag != h.pagina:
                avisos.append(f"{etiqueta}: se tomó como la hoja de las figuras {(pag - 1) * 5 + 1} "
                              f"a {pag * 5} (la comparación con las figuras modelo era dudosa)")
            if pag in por_pagina:
                raise ErrorHoja(
                    f"La {por_pagina[pag][0]} y la {etiqueta} fueron reconocidas "
                    f"como la misma hoja: figuras {(pag - 1) * 5 + 1} a {pag * 5}. "
                    "Revisa esas dos fotos. Si muestran hojas distintas, el sistema pudo "
                    "confundirlas; vuelve a fotografiarlas completas, de frente y con buena luz.")
            por_pagina[pag] = (etiqueta, h)
        faltan = [p for p in (1, 2, 3) if p not in por_pagina]
        if faltan:
            rangos = ", ".join(f"figuras {(p - 1) * 5 + 1} a {p * 5}" for p in faltan)
            raise ErrorHoja(f"Faltan hojas: no encontré la de las {rangos}. Se necesitan las 3 hojas.")
        fotos: dict[str, Path] = {}
        for pag in (1, 2, 3):
            nombre, h = por_pagina[pag]
            for a in h.avisos:
                avisos.append(f"hoja de las figuras {(pag - 1) * 5 + 1} a {pag * 5}: {a}")
            for i, celda in enumerate(h.copias):
                fid = ids[(pag - 1) * 5 + i]
                ok, jpg = cv2.imencode(".jpg", normalizar_celda(celda), [cv2.IMWRITE_JPEG_QUALITY, 95])
                fotos[fid] = self.guardar_foto(child_id, fid, jpg.tobytes(), ".jpg")
                if h.toca_borde[i]:
                    avisos.append(f"{fid}: el trazo toca el borde de la casilla (revisar el recorte)")
        return fotos, avisos

    def evaluar_sesion(
        self, child_id: str, edad_meses: int, fotos: dict[str, str | Path],
        nombre_nino: str | None = None, avisos_previos: list[str] | None = None,
        fecha_evaluacion: str | None = None,
        fecha_nacimiento: str | None = None,
        tipo_avatar: str | None = None,
    ) -> dict:
        preds, X, avisos = [], [], list(avisos_previos or [])
        for fid, ruta in fotos.items():
            if fid not in self.plantillas:
                avisos.append(f"sin plantilla para {fid}, figura omitida")
                continue
            pre = preprocesar_figura(
                str(ruta), self.plantillas[fid],
                self.cfg.get("preprocesamiento", default={}),
            )
            if pre.aviso:
                avisos.append(f"{fid}: {pre.aviso}")
            meta = self.figuras_meta.get(fid, {})
            r = self.final.predecir(pre.figura_bin, fid, self.plantillas[fid], meta, pre.sin_trazo)
            vec = extraer_indicadores(pre.figura_bin, self.plantillas[fid], fid, meta)
            preds.append(PrediccionFigura(
                figura_id=fid, puntaje=r["nota"], prob=r["prob"], decision=r["decision"],
                indicadores={k: round(float(vec.valores[k]), 3) for k in ORDEN}))
            X.append(self.final.fila(pre.figura_bin, fid, self.plantillas[fid], meta)[0])

        sesion = agregar_sesion(child_id, edad_meses, preds)
        tPc, nivel = self._nivel(sesion.PD, edad_meses)

        shap_out = shap_por_sesion(self.modelo, np.array(X, dtype=float), self.nombres,
                                   [p.figura_id for p in preds])
        nombres_fig = {fid: m.get("nombre", fid) for fid, m in self.cfg.figuras.items()}

        exp = explicar_para_docente(
            sesion, nivel, shap_out, nombres_fig, self.exp_cfg, nombre_nino
        )
        por_revisar = [p.figura_id for p in preds if p.decision == "revisar"]
        if self.final:
            # con el modelo final la confianza media baja es normal: el aviso útil es cuáles figuras revisar
            exp.aviso_confianza = None
            if por_revisar:
                nombres_rev = ", ".join(nombres_fig.get(f, f) for f in por_revisar)
                exp.aviso_confianza = (
                    f"Hay {len(por_revisar)} figura(s) que el sistema no se atreve a calificar y conviene "
                    f"que las revises tú: {nombres_rev}. La puntuación total es provisional hasta que las "
                    "califiques.")
        informe = construir_informe(exp)

        panel = informe.panel_tecnico
        panel["resumen"].update({
            "PD": sesion.PD, "percentil": tPc["percentil"], "tramo_edad": tPc["tramo"],
            "nivel": nivel.nivel,
            # instantánea de la IA, no se vuelve a tocar aunque el docente corrija después
            "PD_ia": sesion.PD, "nivel_ia": nivel.nivel,
        })
        panel["avisos_preprocesamiento"] = avisos
        if self.final:
            panel["revision"] = {
                "figuras_por_revisar": por_revisar, "n_automaticas": len(preds) - len(por_revisar),
                "limites": [self.final.li, self.final.ls], "modelo": self.final.manifiesto.get("version", ""),
            }

        resultado = {
            "child_id": child_id,
            "nombre_nino": nombre_nino,
            "edad_meses": edad_meses,
            "fecha_evaluacion": fecha_evaluacion,
            "fecha_nacimiento": fecha_nacimiento,
            "tipo_avatar": tipo_avatar,
            "informe_docente_md": informe.informe_docente_md,
            "accion": exp.accion,
            "accion_ia": exp.accion,  # instantánea, no se toca al corregir
            "aviso_confianza": exp.aviso_confianza,
            "panel_tecnico": panel,
            "figuras": [
                {
                    "figura_id": p.figura_id,
                    "nombre": nombres_fig.get(p.figura_id, p.figura_id),
                    "puntaje": p.puntaje,
                    "puntaje_docente": None,
                    "prob": p.prob,
                    "indicadores": p.indicadores,
                    "decision": p.decision or None,
                }
                for p in preds
            ],
            "version_baremo": self.manifiesto.get("version_baremo", ""),
            "modelo_git_hash": self.manifiesto.get("git_hash", ""),
            "alertas_estilo": informe.alertas_estilo,
        }
        resultado["id"] = db.guardar_sesion(self.db_path, resultado)
        return resultado

    # ------------------------------------------------------------------ #
    def listar_sesiones(self) -> list[dict]:
        return db.listar_sesiones(self.db_path)

    def listar_sesiones_de_nino(self, child_id: str) -> list[dict]:
        return db.listar_sesiones_de_nino(self.db_path, child_id)

    def obtener_sesion(self, sesion_id: int) -> dict | None:
        return db.obtener_sesion(self.db_path, sesion_id)

    def corregir_figura(self, sesion_id: int, figura_id: str, puntaje_docente: int) -> dict | None:
        """Aplica la corrección manual del docente y RECALCULA PD/T/percentil/nivel/acción
        a partir de los puntajes vigentes (corregidos donde los haya, de la IA en el resto).
        Sin esto, el informe seguiría mostrando el resultado original de la IA aunque el
        docente ya lo haya corregido."""
        resultado = db.obtener_sesion(self.db_path, sesion_id)
        if resultado is None:
            return None
        if not any(f["figura_id"] == figura_id for f in resultado["figuras"]):
            return None
        for f in resultado["figuras"]:
            if f["figura_id"] == figura_id:
                f["puntaje_docente"] = int(puntaje_docente)

        pd_total = sum(
            (f["puntaje_docente"] if f["puntaje_docente"] is not None else f["puntaje"])
            for f in resultado["figuras"]
        )
        tPc, nivel = self._nivel(pd_total, resultado["edad_meses"])

        resultado["accion"] = nivel.accion
        resultado["panel_tecnico"]["resumen"].update({
            "PD": pd_total, "percentil": tPc["percentil"], "tramo_edad": tPc["tramo"],
            "nivel": nivel.nivel, "descriptor_verbal": nivel.descriptor_verbal,
        })

        db.actualizar_resultado(self.db_path, sesion_id, resultado)
        return resultado
