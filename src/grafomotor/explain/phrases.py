"""
Banco de frases para el informe del docente.

Reglas de redacción (se comprueban en tests/test_plain_language.py):
  - Frases cortas y concretas.
  - Prohibido en la parte del docente: "SHAP", "XGBoost", "feature", "vector",
    "puntuación T", "percentil", "IoU", "Chamfer", "modelo predictivo".
  - Cada dificultad trae un "qué significa" y un "cómo se ve en la hoja".
  - Español de Perú, registro sencillo (docente de educación inicial).
"""
from __future__ import annotations

# nombre corto orientado al docente
NOMBRE = {
    "precision_modelo": "Parecido general con el modelo",
    "vertices": "Esquinas de la figura",
    "error_angular": "Inclinación de los ángulos",
    "cierre": "Cierre de las figuras",
    "intersecciones": "Cruce de líneas",
    "proporcion": "Tamaño de las partes",
}

# frase cuando el indicador AYUDÓ (punto fuerte)
FORTALEZA = {
    "precision_modelo": "En general, sus dibujos se parecen bastante al modelo.",
    "vertices": "Mantiene bien la forma de las figuras: no le sobran ni le faltan esquinas.",
    "error_angular": "Hace las esquinas con una inclinación parecida a la del modelo.",
    "cierre": "Cierra bien las figuras: las líneas se juntan donde deben.",
    "intersecciones": "Cuando dos líneas se tienen que cruzar, las cruza en el punto correcto.",
    "proporcion": "Respeta el tamaño de las partes: dibuja proporcionado.",
}

# dificultad por severidad -> {que_significa, como_se_ve}
DIFICULTAD = {
    "precision_modelo": {
        "leve": {
            "que_significa": "Su dibujo se parece al modelo, pero con varios detalles fuera de sitio.",
            "como_se_ve": "La figura se reconoce, aunque algo deformada respecto al ejemplo.",
        },
        "moderada": {
            "que_significa": "Le cuesta reproducir la figura tal como es: cambia partes importantes.",
            "como_se_ve": "El dibujo recuerda al modelo, pero hay que fijarse para reconocerlo.",
        },
        "marcada": {
            "que_significa": "Todavía no logra copiar la figura: el resultado se aleja mucho del modelo.",
            "como_se_ve": "Cuesta relacionar su dibujo con el ejemplo que copió.",
        },
    },
    "vertices": {
        "leve": {
            "que_significa": "A veces redondea alguna esquina o añade un pico de más.",
            "como_se_ve": "Un cuadrado con una esquina redonda, o un triángulo con cuatro puntas.",
        },
        "moderada": {
            "que_significa": "Pierde parte de la forma: le faltan o le sobran esquinas.",
            "como_se_ve": "El cuadrado parece un óvalo, o aparecen puntas donde no debería haberlas.",
        },
        "marcada": {
            "que_significa": "No conserva la estructura de la figura; las esquinas casi no aparecen.",
            "como_se_ve": "Trazos curvos o sueltos en vez de una figura con esquinas claras.",
        },
    },
    "error_angular": {
        "leve": {
            "que_significa": "Hace las esquinas, pero con una inclinación algo distinta a la del modelo.",
            "como_se_ve": "Un rombo que sale más 'tumbado' o más 'parado' que el ejemplo.",
        },
        "moderada": {
            "que_significa": "Le cuesta orientar los ángulos: las líneas se juntan con ángulos torcidos.",
            "como_se_ve": "Una cruz cuyos brazos no forman ángulos rectos, o líneas que se abren.",
        },
        "marcada": {
            "que_significa": "Los ángulos no siguen la orientación del modelo; la figura queda desencajada.",
            "como_se_ve": "Esquinas muy abiertas o muy cerradas respecto al ejemplo.",
        },
    },
    "cierre": {
        "leve": {
            "que_significa": "Casi siempre cierra las figuras, con algún huequito suelto.",
            "como_se_ve": "Una esquina del cuadrado que no llega a juntarse por poco.",
        },
        "moderada": {
            "que_significa": "Le cuesta hacer que las líneas se encuentren: varias figuras quedan abiertas.",
            "como_se_ve": "Cuadrados o rombos con un lado que no cierra.",
        },
        "marcada": {
            "que_significa": "Las figuras quedan abiertas: no une los extremos de las líneas.",
            "como_se_ve": "Trazos que empiezan y terminan sin encontrarse.",
        },
    },
    "intersecciones": {
        "leve": {
            "que_significa": "Cruza las líneas, pero el punto de cruce se le desplaza un poco.",
            "como_se_ve": "Una cruz cuyo centro queda algo desplazado.",
        },
        "moderada": {
            "que_significa": "Le cuesta hacer coincidir el cruce de las líneas en el sitio correcto.",
            "como_se_ve": "En la cruz o el aspa, las líneas se cruzan lejos del centro.",
        },
        "marcada": {
            "que_significa": "No consigue que las líneas se crucen donde deben; a veces ni se tocan.",
            "como_se_ve": "Dos líneas paralelas o que se cruzan en un extremo.",
        },
    },
    "proporcion": {
        "leve": {
            "que_significa": "Dibuja las partes con tamaños algo desiguales respecto al modelo.",
            "como_se_ve": "Un lado del cuadrado bastante más largo que los otros.",
        },
        "moderada": {
            "que_significa": "Le cuesta mantener las proporciones: unas partes salen mucho mayores que otras.",
            "como_se_ve": "Una cruz con un brazo largo y otro muy corto.",
        },
        "marcada": {
            "que_significa": "No conserva el tamaño relativo de las partes; la figura queda descompensada.",
            "como_se_ve": "Figuras muy alargadas o aplastadas comparadas con el ejemplo.",
        },
    },
}

# encabezado de resultado por acción (sin cifras)
ENCABEZADO = {
    "ninguna": (
        "El desempeño grafomotor de {nombre} es **adecuado para su edad**. "
        "No se observan señales de alerta."
    ),
    "reforzar_y_revaluar": (
        "Conviene **prestar atención**: {nombre} muestra un desempeño grafomotor "
        "**por debajo de lo esperado** para su edad. Se recomienda reforzarlo en el "
        "aula y volver a evaluarlo dentro de unas semanas."
    ),
    "derivar": (
        "**Se recomienda derivar** a {nombre} a una evaluación con un especialista. "
        "Su desempeño grafomotor está **bastante por debajo** de lo esperado para su edad."
    ),
}

CAUTELA = (
    "Este informe es una **ayuda para el docente**, no un diagnóstico. "
    "La decisión final corresponde a un profesional (psicólogo o especialista)."
)

AVISO_CONFIANZA_BAJA = (
    "⚠️ El sistema tuvo dificultad para leer con claridad algunas figuras "
    "(posiblemente fotos poco nítidas o mal encuadradas). "
    "Revisa este informe con cuidado y, si puedes, repite las fotos."
)


def frase_en_figuras(nombres: list[str]) -> str:
    """'se ve sobre todo en el cuadrado y en el rombo'."""
    nombres = [n for n in nombres if n]
    if not nombres:
        return ""
    if len(nombres) == 1:
        return f"Se ve sobre todo en el/la {nombres[0]}."
    return f"Se ve sobre todo en el/la {nombres[0]} y en el/la {nombres[1]}."
