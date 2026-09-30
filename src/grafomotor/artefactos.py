"""
Nombres y rutas de TODOS los archivos que produce la cadena, en un solo lugar.

Ningún otro módulo debe escribir a mano "oof_dl_<variante>.parquet" ni similares: así
un cambio de convención se hace aquí y los comandos que leen y escriben siguen de acuerdo.

Una *variante* del modelo B es la combinación arquitectura + perfil de aumento
(p. ej. `resnet18`, `resnet18_robusto`, `efficientnet_b0`); con varias semillas, la
semilla i > 0 añade el sufijo `_s<i>`.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from grafomotor.config import Config

AUMENTO_POR_DEFECTO = "moderado"
LADO_POR_DEFECTO = 224


def nombre_variante(arquitectura: str, aumento: str = AUMENTO_POR_DEFECTO,
                    semilla_idx: int = 0, lado: int = LADO_POR_DEFECTO) -> str:
    """p. ej. resnet18 · resnet18_robusto · resnet18_320px · resnet18_robusto_320px_s2."""
    nombre = arquitectura if aumento == AUMENTO_POR_DEFECTO else f"{arquitectura}_{aumento}"
    if lado != LADO_POR_DEFECTO:
        nombre += f"_{lado}px"
    return nombre if semilla_idx == 0 else f"{nombre}_s{semilla_idx}"


def es_semilla_extra(variante: str) -> bool:
    base, _, sufijo = variante.rpartition("_s")
    return bool(base) and sufijo.isdigit()


@dataclass(frozen=True)
class Artefactos:
    procesados: Path
    modelos: Path
    interim_dl: Path

    @classmethod
    def de_config(cls, cfg: Config) -> Artefactos:
        return cls(cfg.ruta("processed"), cfg.ruta("models"), cfg.ruta("interim_dl"))

    # --- compartidos ---------------------------------------------------------
    @property
    def particiones(self) -> Path:
        return self.procesados / "particiones.csv"

    # --- modelo A ------------------------------------------------------------
    @property
    def features(self) -> Path:
        return self.procesados / "features.parquet"

    @property
    def dir_modelo_ml(self) -> Path:
        return self.modelos / "actual"

    @property
    def oof_ml(self) -> Path:
        return self.procesados / "oof_ml.parquet"

    @property
    def evaluacion_ml(self) -> Path:
        return self.procesados / "evaluacion_ml.json"

    # --- modelo B ------------------------------------------------------------
    def carpeta_dl(self, lado: int = LADO_POR_DEFECTO) -> Path:
        """Recortes del modelo B: data/interim_dl (224 px) o data/interim_dl_<lado>."""
        if lado == LADO_POR_DEFECTO:
            return self.interim_dl
        return self.interim_dl.with_name(f"{self.interim_dl.name}_{lado}")

    def preparacion_dl_de(self, lado: int = LADO_POR_DEFECTO) -> Path:
        return self.carpeta_dl(lado) / "_preparacion_dl.csv"

    @property
    def preparacion_dl(self) -> Path:
        return self.preparacion_dl_de(LADO_POR_DEFECTO)

    def lado_de_variante(self, variante: str) -> int:
        """Resolución con que se entrenó una variante (guardada en su historial)."""
        import json

        ruta = self.historial_dl(variante)
        if not ruta.exists():
            return LADO_POR_DEFECTO
        cfg = json.loads(ruta.read_text(encoding="utf-8")).get("cfg", {})
        return int(cfg.get("lado_px", LADO_POR_DEFECTO))

    def dir_modelo_dl(self, variante: str) -> Path:
        return self.modelos / "dl" / variante

    def modelo_dl_fold(self, variante: str, fold: int) -> Path:
        return self.dir_modelo_dl(variante) / f"fold{fold}.pt"

    def modelo_dl_final(self, variante: str) -> Path:
        return self.dir_modelo_dl(variante) / "final.pt"

    def historial_dl(self, variante: str) -> Path:
        return self.dir_modelo_dl(variante) / "historial.json"

    def oof_dl(self, variante: str) -> Path:
        return self.procesados / f"oof_dl_{variante}.parquet"

    def evaluacion_dl(self, variante: str) -> Path:
        return self.procesados / f"evaluacion_dl_{variante}.json"

    def variabilidad_dl(self, variante: str) -> Path:
        return self.procesados / f"variabilidad_dl_{variante}.json"

    def variantes_dl(self) -> list[str]:
        """Variantes con evaluación guardada (sin las semillas extra)."""
        return sorted(v for p in self.procesados.glob("evaluacion_dl_*.json")
                      if not es_semilla_extra(v := p.stem.removeprefix("evaluacion_dl_")))

    # --- comparación ---------------------------------------------------------
    def comparacion(self, variante: str, ext: str = "json") -> Path:
        return self.procesados / f"comparacion_{variante}.{ext}"

    def robustez(self, variante: str, ext: str = "json") -> Path:
        return self.procesados / f"robustez_{variante}.{ext}"

    @property
    def cache_robustez_ml(self) -> Path:
        return self.procesados / "robustez_A_cache.parquet"

    def gradcam(self, variante: str) -> Path:
        return self.procesados / f"gradcam_{variante}.json"

    def dir_ejemplos_gradcam(self, variante: str) -> Path:
        return self.procesados / f"gradcam_{variante}"

    def practicidad(self, variante: str) -> Path:
        return self.procesados / f"practicidad_{variante}.json"

    def dir_errores(self, modelo: str) -> Path:
        """Galería de errores de un modelo ("ml" para A o el nombre de una variante de B)."""
        return self.procesados / f"errores_{modelo}"

    @property
    def acuerdo_evaluadores(self) -> Path:
        return self.procesados / "acuerdo_evaluadores.json"

    @property
    def resumen_variantes(self) -> Path:
        return self.procesados / "resumen_variantes.md"
