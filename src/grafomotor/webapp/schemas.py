"""Contratos de la API."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


TipoAvatar = Literal["nino", "nina"]


class FiguraOut(BaseModel):
    figura_id: str
    nombre: str
    puntaje: int
    puntaje_docente: int | None = None
    prob: float
    indicadores: dict[str, float]
    decision: str | None = Field(
        default=None, description="correcta | incorrecta | revisar (la califica el docente)")


class EvaluarOut(BaseModel):
    id: int
    child_id: str
    nombre_nino: str | None = None
    edad_meses: int
    fecha_nacimiento: str | None = None
    tipo_avatar: TipoAvatar | None = None
    numero_avatar: int | None = None
    fecha_evaluacion: str | None = None   # AAAA-MM-DD; la edad se calculó a esta fecha
    # --- para el docente ---
    informe_docente_md: str
    accion: str = Field(
        description="ninguna | reforzar_y_revaluar | derivar (con correcciones aplicadas)")
    accion_ia: str | None = Field(
        default=None, description="acción original de la IA, sin correcciones del docente")
    aviso_confianza: str | None = None
    # --- para el especialista (panel aparte) ---
    panel_tecnico: dict
    figuras: list[FiguraOut]
    # trazabilidad
    version_baremo: str
    modelo_git_hash: str


class FiguraSeguimiento(BaseModel):
    figura_id: str
    nombre: str = ""
    puntaje: int
    puntaje_docente: int | None = None
    decision: str | None = None


class SesionResumen(BaseModel):
    id: int
    child_id: str
    nombre_nino: str | None = None
    edad_meses: int
    fecha_nacimiento: str | None = None
    tipo_avatar: TipoAvatar | None = None
    fecha: str
    pd_total: int
    nivel: str
    accion: str
    percentil: float | None = None
    figuras: list[FiguraSeguimiento] = Field(default_factory=list)


class CorregirFiguraIn(BaseModel):
    puntaje_docente: int = Field(ge=0, le=1)
