"""
Orquestador de inferencia: junta todas las etapas para una sesión (un niño).

foto(s) -> preprocesar -> extraer indicadores -> XGBoost (puntaje por figura) ->
scoring (PD -> T -> nivel) -> SHAP -> explicación en lenguaje natural -> se guarda
en SQLite (data/app.db) para que el Dashboard Docente tenga historial real.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from grafomotor.config import load_config
from grafomotor.evaluation import estratificar_por_tramo  # noqa: F401  (para scripts)
from grafomotor.explain import construir_informe, explicar_para_docente, shap_por_sesion
from grafomotor import ORDEN
from grafomotor.features.extract import extraer_indicadores
from grafomotor.model.predict import agregar_sesion, predecir_figura
from grafomotor.model.registry import cargar_modelo
from grafomotor.preprocessing import preprocesar_figura
from grafomotor.scoring.baremo import cargar_baremo, pd_a_T
from grafomotor.scoring.niveles import nivel_desde_T
from grafomotor.webapp import db


class Servicio:
    """Carga modelo + baremo + plantillas una sola vez y sirve evaluaciones."""

    def __init__(self, config_path: str | None = None):
        self.cfg = load_config(config_path)
        self.modelo, self.manifiesto = cargar_modelo(self.cfg.ruta("models") / "actual")
        self.baremo = cargar_baremo(self.cfg.ruta("baremos"))
        self.plantillas = self._cargar_plantillas()
        self.figuras_meta = self.cfg.figuras
        self.exp_cfg = self.cfg.get("explicacion", default={})
        self.sco_cfg = self.cfg.get("scoring", default={})
        self.db_path = self.cfg.ruta("db")
        db.iniciar_db(self.db_path)

    def _cargar_plantillas(self) -> dict[str, np.ndarray]:
        carpeta = self.cfg.ruta("templates")
        out = {}
        for fid in self.cfg.figuras:
            p = carpeta / f"{fid}.png"
            if p.exists():
                img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
                out[fid] = (img > 127).astype(np.uint8) * 255
        return out

    def ruta_plantilla(self, figura_id: str) -> Path | None:
        p = self.cfg.ruta("templates") / f"{figura_id}.png"
        return p if p.exists() else None

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
            vec = extraer_indicadores(
                pre.figura_bin, self.plantillas[fid], fid, self.figuras_meta.get(fid, {})
            )
            preds.append(predecir_figura(self.modelo, vec.valores, fid))
            X.append([vec.valores[k] for k in ORDEN])

        sesion = agregar_sesion(child_id, edad_meses, preds)
        tT = pd_a_T(sesion.PD, edad_meses, self.baremo)
        nivel = nivel_desde_T(
            tT["T"],
            n_clases=int(self.sco_cfg.get("n_clases", 2)),
            corte_bajo=int(self.sco_cfg.get("corte_bajo_T", 40)),
            corte_muy_bajo=int(self.sco_cfg.get("corte_muy_bajo_T", 30)),
        )

        shap_out = shap_por_sesion(self.modelo, np.array(X, dtype=float), list(ORDEN))
        nombres_fig = {fid: m.get("nombre", fid) for fid, m in self.figuras_meta.items()}

        exp = explicar_para_docente(
            sesion, nivel, shap_out, nombres_fig, self.exp_cfg, nombre_nino
        )
        informe = construir_informe(exp)

        panel = informe.panel_tecnico
        panel["resumen"].update({
            "PD": sesion.PD, "percentil": tT["percentil"], "tramo_edad": tT["tramo"],
            "nivel": nivel.nivel,
            # instantánea de la IA, no se vuelve a tocar aunque el docente corrija después
            "PD_ia": sesion.PD, "nivel_ia": nivel.nivel,
        })
        panel["avisos_preprocesamiento"] = avisos

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
        tT = pd_a_T(pd_total, resultado["edad_meses"], self.baremo)
        nivel = nivel_desde_T(
            tT["T"],
            n_clases=int(self.sco_cfg.get("n_clases", 2)),
            corte_bajo=int(self.sco_cfg.get("corte_bajo_T", 40)),
            corte_muy_bajo=int(self.sco_cfg.get("corte_muy_bajo_T", 30)),
        )

        resultado["accion"] = nivel.accion
        resultado["panel_tecnico"]["resumen"].update({
            "PD": pd_total, "T": nivel.T, "percentil": tT["percentil"], "tramo_edad": tT["tramo"],
            "nivel": nivel.nivel, "descriptor_verbal": nivel.descriptor_verbal,
        })

        db.actualizar_resultado(self.db_path, sesion_id, resultado)
        return resultado
