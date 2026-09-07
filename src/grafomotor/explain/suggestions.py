"""
Sugerencias de actividad de aula por indicador débil (niños de 3 a 5 años).

Actividades sencillas, con material de aula, que un docente de inicial pueda aplicar
sin formación clínica. 2 por indicador; se eligen las 2 primeras.
"""
from __future__ import annotations

ACTIVIDADES: dict[str, list[str]] = {
    "precision_modelo": [
        "Copiar figuras grandes puestas al lado del papel (no de memoria), primero con "
        "el dedo en el aire y luego con crayola.",
        "Juego de 'igualito al mío': el docente dibuja una figura simple y el niño la "
        "reproduce en su hoja mirando el modelo.",
    ],
    "vertices": [
        "Trazar figuras uniendo puntos marcados en las esquinas (dot-to-dot) para que "
        "'sienta' dónde va cada esquina.",
        "Formar cuadrados y triángulos con palitos o limpiapipas antes de dibujarlos, "
        "para reconocer cuántas esquinas tienen.",
    ],
    "error_angular": [
        "Repasar esquinas con una plantilla o escuadra de cartón, parando en cada "
        "vértice antes de seguir.",
        "Juego de 'esquina de robot': marcar el giro en cada esquina con un golpecito "
        "del lápiz y contar '1-2-3' antes de girar.",
    ],
    "cierre": [
        "Laberintos y caminos cerrados donde tiene que 'volver a la puerta' sin dejar "
        "huecos.",
        "Rodear objetos y siluetas con el lápiz haciendo que la línea llegue hasta el "
        "punto de partida (ponerle una pegatina en el inicio).",
    ],
    "intersecciones": [
        "Dibujar cruces y aspas sobre un punto central marcado con color, empezando "
        "siempre desde ese punto.",
        "Juego de 'las calles se cruzan': trazar dos líneas que deben pasar por un "
        "semáforo (punto) dibujado en el centro.",
    ],
    "proporcion": [
        "Copiar figuras sobre papel cuadriculado grande, contando cuadraditos por lado.",
        "Comparar 'grande y chico': dibujar la misma figura en dos tamaños y luego "
        "copiar una intermedia mirando el modelo.",
    ],
}

GENERALES = [
    "Actividades de motricidad fina previas al trazo: pinzas, ensartado, plastilina, "
    "rasgado de papel.",
    "Trabajar sentado con buena postura y sujeción del lápiz (pinza trípode), en "
    "sesiones cortas y frecuentes.",
]


def sugerencias_para(indicadores_debiles: list[str], n_por_indicador: int = 2) -> list[str]:
    out: list[str] = []
    for ind in indicadores_debiles:
        out.extend(ACTIVIDADES.get(ind, [])[:n_por_indicador])
    if not out:
        out = GENERALES[:]
    # sin repetidos, manteniendo orden
    vistos, unicas = set(), []
    for s in out:
        if s not in vistos:
            vistos.add(s)
            unicas.append(s)
    return unicas
