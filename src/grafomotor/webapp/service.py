"""
Orquestador de inferencia: junta todas las etapas para una sesión (un niño).

foto(s) -> preprocesar -> extraer indicadores -> XGBoost (puntaje por figura) ->
scoring (PD -> T -> nivel) -> SHAP -> explicación en lenguaje natural.
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

    def _cargar_plantillas(self) -> dict[str, np.ndarray]:
        carpeta = self.cfg.ruta("templates")
        out = {}
        for fid in self.cfg.figuras:
            p = carpeta / f"{fid}.png"
            if p.exists():
                img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
                out[fid] = (img > 127).astype(np.uint8) * 255
        return out

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
        panel["resumen"].update({"percentil": tT["percentil"], "tramo_edad": tT["tramo"]})
        panel["avisos_preprocesamiento"] = avisos

        return {
            "child_id": child_id,
            "edad_meses": edad_meses,
            "informe_docente_md": informe.informe_docente_md,
            "accion": exp.accion,
            "aviso_confianza": exp.aviso_confianza,
            "panel_tecnico": panel,
            "figuras": [
                {
                    "figura_id": p.figura_id,
                    "nombre": nombres_fig.get(p.figura_id, p.figura_id),
                    "puntaje": p.puntaje,
                    "prob": p.prob,
                    "indicadores": p.indicadores,
                }
                for p in preds
            ],
            "version_baremo": self.manifiesto.get("version_baremo", ""),
            "modelo_git_hash": self.manifiesto.get("git_hash", ""),
            "alertas_estilo": informe.alertas_estilo,
        }
