"""
Traducción de SHAP + indicadores -> hallazgos en lenguaje natural para el docente.

Entrada:
  sesion       : PrediccionSesion  (figuras con puntaje/prob/indicadores)
  nivel        : NivelResultado    (T, nivel, accion)
  shap         : dict de shap_por_sesion()  (agg_signed, agg_abs, por_figura)
  nombres_fig  : {figura_id: "cuadrado", ...}
  nombre_nino  : str | None

Salida: Explicacion (dict-friendly) que report.py convierte en texto/HTML.
"""
from __future__ import annotations

import html
from dataclasses import dataclass, field

from grafomotor.explain import phrases as P
from grafomotor.explain.suggestions import sugerencias_para

# palabras que NO deben aparecer en el texto para el docente
JERGA_PROHIBIDA = [
    "shap", "xgboost", "feature", "vector", "puntuación t", "puntuacion t",
    "percentil", "iou", "chamfer", "modelo predictivo", "log-odds", "gradient",
    "dataset", "baremo",
]


@dataclass
class Hallazgo:
    indicador: str
    nombre: str
    tipo: str                 # "fortaleza" | "dificultad"
    severidad: str | None     # None para fortaleza; leve/moderada/marcada
    que_significa: str
    como_se_ve: str
    en_figuras: str           # "Se ve sobre todo en el cuadrado y en el rombo."
    influencia: float         # |shap| agregado, para ordenar (uso interno)


@dataclass
class Explicacion:
    nombre_nino: str
    encabezado: str
    accion: str               # ninguna | reforzar_y_revaluar | derivar
    aviso_confianza: str | None
    fortalezas: list[Hallazgo]
    dificultades: list[Hallazgo]
    sugerencias: list[str]
    cautela: str
    # datos crudos para el panel técnico (no se muestran al docente)
    tecnico: dict = field(default_factory=dict)


def _severidad(valor_medio: float) -> str | None:
    if valor_medio >= 0.75:
        return None
    if valor_medio >= 0.55:
        return "leve"
    if valor_medio >= 0.35:
        return "moderada"
    return "marcada"


def _valor_medio_indicador(sesion, ind: str) -> float:
    vals = [f.indicadores[ind] for f in sesion.figuras if ind in f.indicadores]
    return sum(vals) / len(vals) if vals else 1.0


def _peores_figuras(sesion, ind: str, nombres_fig: dict, k: int = 2) -> list[str]:
    ordenadas = sorted(sesion.figuras, key=lambda f: f.indicadores.get(ind, 1.0))
    return [nombres_fig.get(f.figura_id, f.figura_id) for f in ordenadas[:k]]


def _mejores_figuras(sesion, ind: str, nombres_fig: dict, k: int = 2) -> list[str]:
    ordenadas = sorted(sesion.figuras, key=lambda f: -f.indicadores.get(ind, 0.0))
    return [nombres_fig.get(f.figura_id, f.figura_id) for f in ordenadas[:k]]


def explicar_para_docente(
    sesion,
    nivel,
    shap: dict,
    nombres_fig: dict[str, str],
    cfg: dict,
    nombre_nino: str | None = None,
) -> Explicacion:
    # escapado por seguridad: nombre_nino llega del formulario del docente y este
    # texto se renderiza luego como HTML en el Dashboard (markdown -> HTML)
    nombre = html.escape(nombre_nino) if nombre_nino else "el niño / la niña"
    umbral = float(cfg.get("umbral_relevancia_shap", 0.03))
    max_fort = int(cfg.get("max_fortalezas", 2))
    max_dif = int(cfg.get("max_dificultades", 3))
    umbral_conf = float(cfg.get("umbral_confianza_baja", 0.60))

    agg = shap["agg_signed"]

    # --- dificultades: indicadores que empujaron hacia "incorrecta" (shap negativo) ---
    dif_candidatos = sorted(
        [i for i, v in agg.items() if v <= -umbral],
        key=lambda i: agg[i],  # más negativo primero
    )
    dificultades: list[Hallazgo] = []
    for ind in dif_candidatos:
        vmed = _valor_medio_indicador(sesion, ind)
        sev = _severidad(vmed)
        if sev is None:                      # el indicador no está realmente bajo
            continue
        d = P.DIFICULTAD[ind][sev]
        dificultades.append(Hallazgo(
            indicador=ind, nombre=P.NOMBRE[ind], tipo="dificultad", severidad=sev,
            que_significa=d["que_significa"], como_se_ve=d["como_se_ve"],
            en_figuras=P.frase_en_figuras(_peores_figuras(sesion, ind, nombres_fig)),
            influencia=abs(agg[ind]),
        ))
        if len(dificultades) >= max_dif:
            break

    # --- fortalezas: indicadores que ayudaron (shap positivo) y con valor alto ---
    fort_candidatos = sorted(
        [i for i, v in agg.items() if v >= umbral],
        key=lambda i: -agg[i],
    )
    fortalezas: list[Hallazgo] = []
    for ind in fort_candidatos:
        if _valor_medio_indicador(sesion, ind) < 0.6:
            continue
        fortalezas.append(Hallazgo(
            indicador=ind, nombre=P.NOMBRE[ind], tipo="fortaleza", severidad=None,
            que_significa=P.FORTALEZA[ind], como_se_ve="",
            en_figuras=P.frase_en_figuras(_mejores_figuras(sesion, ind, nombres_fig)),
            influencia=abs(agg[ind]),
        ))
        if len(fortalezas) >= max_fort:
            break

    # si no hubo fortalezas claras pero el nivel es adecuado, dar una genérica
    if not fortalezas and nivel.accion == "ninguna":
        mejor = max(agg, key=lambda i: _valor_medio_indicador(sesion, i))
        fortalezas.append(Hallazgo(
            indicador=mejor, nombre=P.NOMBRE[mejor], tipo="fortaleza", severidad=None,
            que_significa=P.FORTALEZA[mejor], como_se_ve="",
            en_figuras="", influencia=0.0,
        ))

    aviso = P.AVISO_CONFIANZA_BAJA if sesion.confianza_media < umbral_conf else None

    return Explicacion(
        nombre_nino=nombre,
        encabezado=P.ENCABEZADO[nivel.accion].format(nombre=nombre),
        accion=nivel.accion,
        aviso_confianza=aviso,
        fortalezas=fortalezas,
        dificultades=dificultades,
        sugerencias=sugerencias_para([d.indicador for d in dificultades]),
        cautela=P.CAUTELA,
        tecnico={
            "T": nivel.T,
            "nivel": nivel.nivel,
            "descriptor_verbal": nivel.descriptor_verbal,
            "PD": sesion.PD,
            "n_figuras": sesion.n_figuras,
            "confianza_media": sesion.confianza_media,
            "shap_agregado": {k: round(v, 4) for k, v in agg.items()},
        },
    )


def contiene_jerga(texto: str) -> list[str]:
    """Devuelve la jerga encontrada (para el test de estilo)."""
    low = texto.lower()
    return [j for j in JERGA_PROHIBIDA if j in low]
