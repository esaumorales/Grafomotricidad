"""Contratos de la API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class FiguraOut(BaseModel):
    figura_id: str
    nombre: str
    puntaje: int
    prob: float
    indicadores: dict[str, float]


class EvaluarOut(BaseModel):
    child_id: str
    edad_meses: int
    # --- para el docente ---
    informe_docente_md: str
    accion: str = Field(description="ninguna | reforzar_y_revaluar | derivar")
    aviso_confianza: str | None = None
    # --- para el especialista (panel aparte) ---
    panel_tecnico: dict
    figuras: list[FiguraOut]
    # trazabilidad
    version_baremo: str
    modelo_git_hash: str
