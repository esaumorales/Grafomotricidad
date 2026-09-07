"""
(OPCIONAL, DESACTIVADO POR DEFECTO)

Pulido del informe con un LLM: reformula el texto de plantilla en un español aún más
natural para el docente, SIN inventar datos ni cambiar cifras ni recomendaciones.

Para la tesis se recomienda dejarlo apagado: las plantijas deterministas son
reproducibles y auditables. Este módulo es solo un punto de extensión.
"""
from __future__ import annotations

SYSTEM_PROMPT = """\
Eres un asistente que reescribe informes escolares para docentes de educación inicial
en Perú. Recibes un informe ya redactado sobre el desempeño grafomotor de un niño.
Tu tarea: reformularlo en un español claro, cálido y sencillo, en frases cortas.

REGLAS ESTRICTAS:
- No inventes información ni ejemplos que no estén en el texto original.
- No cambies el sentido del resultado ni las recomendaciones.
- No añadas cifras, porcentajes ni terminología técnica.
- Mantén la estructura: resultado, lo que se le da bien, lo que le cuesta, qué hacer,
  y la nota final de que no es un diagnóstico.
- Devuelve solo el informe reformulado, en Markdown.
"""


def pulir(informe_md: str, cfg: dict) -> str:
    if not cfg.get("pulido_llm", {}).get("activar", False):
        return informe_md
    raise NotImplementedError(
        "Pulido por LLM no implementado. Conecta aquí tu cliente (p. ej. la API de "
        "Claude) usando SYSTEM_PROMPT y el informe como mensaje de usuario. "
        "Verifica la salida con explain.plain_language.contiene_jerga()."
    )
