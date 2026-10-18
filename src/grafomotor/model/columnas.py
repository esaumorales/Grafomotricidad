"""
Columnas de entrada del modelo A, definidas en UN solo lugar.

Por defecto el modelo recibe los 6 indicadores normalizados. `config.yaml > modelo > entrada`
puede añadir:
- `crudos: true`  -> las 6 medidas crudas que `extraer-features` ya calcula (columnas raw_*).
- `figura: onehot` -> qué figura se califica (fig_F01 ... fig_F15). Así un único modelo para
  las 15 figuras sabe, por ejemplo, que 4 esquinas están bien en el cuadrado y mal en el
  triángulo.

Las columnas se guardan en el manifiesto del modelo (`feature_names`): la inferencia usa
siempre las del modelo cargado, no las de la configuración actual.

Un valor infinito (p. ej. distancia de cruce cuando el niño no hizo ningún cruce) se pasa a
faltante (NaN): XGBoost no acepta infinitos y aprende hacia qué rama mandar los faltantes.
Solo depende de numpy (lo importa `model.predict`).
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from grafomotor import ORDEN

# medida cruda -> indicador del que sale (para agrupar SHAP en la explicación a la docente)
CRUDOS = {
    "raw_iou": "precision_modelo",
    "raw_n_vertices": "vertices",
    "raw_error_angular_deg": "error_angular",
    "raw_extremos_libres": "cierre",
    "raw_dist_interseccion_px": "intersecciones",
    "raw_razon_aspecto": "proporcion",
}
PREFIJO_FIGURA = "fig_"


def nombres_columnas(cfg) -> list[str]:
    """Columnas de entrada según `modelo.entrada` de la configuración."""
    entrada = cfg.get("modelo", "entrada", default={}) or {}
    nombres = list(ORDEN)
    if entrada.get("crudos", False):
        nombres += list(CRUDOS)
    modo = entrada.get("figura", "ninguna")
    if modo == "onehot":
        nombres += [PREFIJO_FIGURA + f for f in cfg.figuras]
    elif modo != "ninguna":
        raise ValueError(f"modelo.entrada.figura debe ser 'ninguna' u 'onehot', no {modo!r}")
    return nombres


def indicador_de(nombre: str) -> str | None:
    """Indicador al que pertenece una columna; None para las columnas de figura."""
    if nombre in ORDEN:
        return nombre
    return CRUDOS.get(nombre)


def a_finito(x: float) -> float:
    """Infinito -> NaN (faltante); lo demás queda igual."""
    x = float(x)
    return float("nan") if math.isinf(x) else x


def fila(valores: Mapping[str, float], crudos: Mapping[str, float], figura_id: str,
         nombres: Sequence[str]) -> list[float]:
    """Vector de entrada de UNA figura. `crudos` con o sin el prefijo raw_ (como VectorIndicadores.raw)."""
    out = []
    for n in nombres:
        if n.startswith(PREFIJO_FIGURA):
            out.append(1.0 if n[len(PREFIJO_FIGURA):] == figura_id else 0.0)
        elif n in CRUDOS:
            corto = n.removeprefix("raw_")
            out.append(a_finito(crudos[n] if n in crudos else crudos[corto]))
        else:
            out.append(a_finito(valores[n]))
    return out
