"""
Orquestador de inferencia: junta todas las etapas para una sesión (un niño).

foto(s) -> preprocesar -> extraer indicadores -> modelo (puntaje por figura) ->
scoring (PD -> T -> nivel) -> SHAP -> explicación en lenguaje natural -> se guarda
en SQLite (data/app.db) para que el Dashboard Docente tenga historial real.

Modelo: si existe una versión del modelo final (models/final/<versión>/, ver
scripts/instalar_modelo_final.py) se usa ese Random Forest con revisión por confianza (las figuras
dudosas quedan "por revisar" para el docente); si no, el XGBoost antiguo de models/actual.
La versión se elige en config.yaml (modelo_final.version) o con la variable GRAFOMOTOR_MODELO_FINAL.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import numpy as np

from grafomotor import ORDEN
from grafomotor.model.columnas import fila
from grafomotor.artefactos import Artefactos
from grafomotor.config import load_config
from grafomotor.explain import construir_informe, explicar_para_docente, shap_por_sesion
from grafomotor.features.extract import extraer_indicadores
from grafomotor.io import cargar_plantillas, ruta_plantilla
from grafomotor.model.final import ModeloFinal
from grafomotor.model.predict import PrediccionFigura, agregar_sesion, predecir_figura
from grafomotor.model.registry import cargar_modelo
from grafomotor.preprocessing import preprocesar_figura
from grafomotor.scoring.baremo import cargar_baremo, pd_a_percentil
from grafomotor.scoring.niveles import CriterioNiveles, NivelResultado
from grafomotor.webapp import db


log = logging.getLogger(__name__)


class Servicio:
    """Carga modelo + baremo + plantillas una sola vez y sirve evaluaciones."""

    def __init__(self, config_path: str | None = None):
        self.cfg = load_config(config_path)
        self.final = self._cargar_final()
        if self.final:
            self.modelo = self.final.modelo
            self.manifiesto = {"git_hash": self.final.version, "feature_names": self.final.nombres,
                               "version_baremo": str(self.cfg.get("scoring", "version_baremo", default=""))}
            self.plantillas = self.final.plantillas
            self.figuras_meta = self.final.figuras_meta
        else:
            self.modelo, self.manifiesto = cargar_modelo(Artefactos.de_config(self.cfg).dir_modelo_ml)
            self.plantillas = cargar_plantillas(self.cfg, estricto=False)
            self.figuras_meta = self.cfg.figuras
        # columnas con que se entrenó el modelo cargado (los modelos antiguos solo tienen las 6)
        self.nombres = list(self.manifiesto.get("feature_names") or ORDEN)
        self.baremo = cargar_baremo(self.cfg.ruta("baremos"))
        self.exp_cfg = self.cfg.get("explicacion", default={})
        self.sco_cfg = self.cfg.get("scoring", default={})
        self.criterio = CriterioNiveles.de_config(self.cfg)
        self.db_path = self.cfg.ruta("db")
        db.iniciar_db(self.db_path)

    def _cargar_final(self) -> ModeloFinal | None:
        """Versión del modelo final elegida, o None si no está instalada (se usa el modelo antiguo)."""
        elegida = os.environ.get("GRAFOMOTOR_MODELO_FINAL") or self.cfg.get("modelo_final", "version", default="")
        if not elegida:
            return None
        carpeta = Path(elegida)
        if not carpeta.is_absolute():
            carpeta = self.cfg.ruta("models") / "final" / elegida
        if not (carpeta / "modelo.joblib").exists():
            log.warning("modelo final %s no instalado en %s: se usa el modelo antiguo", elegida, carpeta)
            return None
        return ModeloFinal(carpeta)

    def ruta_plantilla(self, figura_id: str) -> Path | None:
        p = (self.final.dir_plantillas / f"{figura_id}.png" if self.final
             else ruta_plantilla(self.cfg, figura_id))
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
    def evaluar_sesion(
        self, child_id: str, edad_meses: int, fotos: dict[str, str | Path],
        nombre_nino: str | None = None,
    ) -> dict:
        preds, X, avisos = [], [], []
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
            if self.final:
                r = self.final.predecir_figura(pre.figura_bin, fid)
                preds.append(PrediccionFigura(
                    figura_id=fid, puntaje=r["nota"], prob=round(r["prob"], 3), decision=r["decision"],
                    indicadores={k: round(float(r["vec"].valores[k]), 3) for k in ORDEN}))
                X.append(r["x"])
                continue
            vec = extraer_indicadores(
                pre.figura_bin, self.plantillas[fid], fid, self.figuras_meta.get(fid, {})
            )
            preds.append(predecir_figura(self.modelo, vec.valores, fid, vec.raw, self.nombres))
            X.append(fila(vec.valores, vec.raw, fid, self.nombres))

        sesion = agregar_sesion(child_id, edad_meses, preds)
        tPc, nivel = self._nivel(sesion.PD, edad_meses)

        shap_out = shap_por_sesion(self.modelo, np.array(X, dtype=float), self.nombres)
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
                "limites": [self.final.li, self.final.ls], "modelo": self.final.version,
            }

        resultado = {
            "child_id": child_id,
            "nombre_nino": nombre_nino,
            "edad_meses": edad_meses,
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
