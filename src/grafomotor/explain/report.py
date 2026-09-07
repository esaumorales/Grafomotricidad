"""
Ensamblado del informe final.

  informe_docente : texto en lenguaje natural (Markdown / HTML). SIN cifras técnicas.
  panel_tecnico   : para el especialista. Aquí SÍ van T, percentil, PD y la tabla SHAP.

Estas dos partes van siempre separadas: el docente lee la narrativa; el especialista,
si quiere, despliega el panel.
"""
from __future__ import annotations

from dataclasses import dataclass

from grafomotor.explain.plain_language import Explicacion, contiene_jerga


@dataclass
class InformeCompleto:
    informe_docente_md: str
    panel_tecnico: dict
    alertas_estilo: list[str]     # jerga detectada en la parte del docente (debe ser [])


def _bloque_dificultad(h) -> str:
    partes = [f"**{h.nombre}** ({h.severidad}). {h.que_significa}"]
    if h.como_se_ve:
        partes.append(f"Cómo se ve en la hoja: {h.como_se_ve}")
    if h.en_figuras:
        partes.append(h.en_figuras)
    return " ".join(partes)


def construir_informe(exp: Explicacion) -> InformeCompleto:
    L: list[str] = []
    L.append(f"## Informe grafomotor — {exp.nombre_nino}\n")

    if exp.aviso_confianza:
        L.append(f"> {exp.aviso_confianza}\n")

    L.append(exp.encabezado + "\n")

    if exp.fortalezas:
        L.append("### Lo que se le da bien")
        for h in exp.fortalezas:
            linea = f"- {h.que_significa}"
            if h.en_figuras:
                linea += f" {h.en_figuras}"
            L.append(linea)
        L.append("")

    if exp.dificultades:
        L.append("### Lo que le cuesta más")
        for h in exp.dificultades:
            L.append(f"- {_bloque_dificultad(h)}")
        L.append("")

    if exp.sugerencias:
        L.append("### Qué puedes hacer en el aula")
        for s in exp.sugerencias:
            L.append(f"- {s}")
        L.append("")

    L.append(f"---\n_{exp.cautela}_")
    md = "\n".join(L)

    return InformeCompleto(
        informe_docente_md=md,
        panel_tecnico={
            "resumen": exp.tecnico,
            "accion": exp.accion,
            "nota": (
                "Panel para el especialista. La puntuación T se obtiene del baremo del "
                "CUMANIN-2 por tramo de edad; T ≤ 40 = en riesgo, T ≤ 30 = derivar "
                "(manual, pág. 98-99). 'shap_agregado' con signo: negativo = el "
                "indicador empujó la puntuación de la figura hacia 'incorrecta'."
            ),
        },
        alertas_estilo=contiene_jerga(md),
    )
