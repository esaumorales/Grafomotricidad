"""Contratos de la API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class FiguraOut(BaseModel):
    figura_id: str
    nombre: str
    puntaje: int
    puntaje_docente: int | None = None
    prob: float
    indicadores: dict[str, float]


class EvaluarOut(BaseModel):
    id: int
    child_id: str
    nombre_nino: str | None = None
    edad_meses: int
    # --- para el docente ---
    informe_docente_md: str
    accion: str = Field(description="ninguna | reforzar_y_revaluar | derivar (con correcciones aplicadas)")
    accion_ia: str | None = Field(default=None, description="acción original de la IA, sin correcciones del docente")
    aviso_confianza: str | None = None
    # --- para el especialista (panel aparte) ---
    panel_tecnico: dict
    figuras: list[FiguraOut]
    # trazabilidad
    version_baremo: str
    modelo_git_hash: str


class SesionResumen(BaseModel):
    id: int
    child_id: str
    nombre_nino: str | None = None
    edad_meses: int
    fecha: str
    pd_total: int
    nivel: str
    accion: str


class CorregirFiguraIn(BaseModel):
    puntaje_docente: int = Field(ge=0, le=1)
