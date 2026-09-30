"""
Nivel de desempeño grafomotor. La forma recomendada es `CriterioNiveles` (cortes y
fuente en config.yaml, por percentil de la Tabla B.9). `nivel_desde_T` se conserva como
criterio histórico.

T -> nivel de desempeño grafomotor. Cortes citados del manual (pág. 98-99),
PENDIENTES DE VALIDAR con el asesor para el CUMANIN original (la T de esta
subescala es una estimación desde el percentil de la Tabla B.9):

    T >= 41  -> Adecuado
    31-40    -> Bajo (en riesgo / screening)
    <= 30    -> Muy bajo (derivar a especialista)

`n_clases`:
  2 -> {Adecuado, En riesgo}      (En riesgo = T <= 40; recomendado por defecto)
  3 -> {Adecuado, Bajo, Muy bajo}

Tabla 5.2 (7 descriptores) disponible en `descriptor_verbal()` para el panel técnico.
"""
from __future__ import annotations

from dataclasses import dataclass

CORTE_BAJO = 40
CORTE_MUY_BAJO = 30

# Tabla 5.2 del manual (descriptor -> (T_min, T_max))
TABLA_5_2 = [
    ("Muy alto", 70, 999),
    ("Alto", 60, 69),
    ("Medio-alto", 55, 59),
    ("Medio", 46, 54),
    ("Medio-bajo", 41, 45),
    ("Bajo", 31, 40),
    ("Muy bajo", -999, 30),
]


@dataclass
class NivelResultado:
    T: float
    nivel: str                 # etiqueta según n_clases
    accion: str                # "ninguna" | "reforzar_y_revaluar" | "derivar"
    descriptor_verbal: str     # de la Tabla 5.2 (para el especialista)
    n_clases: int
    percentil: float | None = None


def descriptor_verbal(T: float) -> str:
    for nombre, lo, hi in TABLA_5_2:
        if lo <= T <= hi:
            return nombre
    return "Medio"


def nivel_desde_T(T: float, n_clases: int = 2, corte_bajo: int = CORTE_BAJO,
                  corte_muy_bajo: int = CORTE_MUY_BAJO) -> NivelResultado:
    if T <= corte_muy_bajo:
        accion = "derivar"
    elif T <= corte_bajo:
        accion = "reforzar_y_revaluar"
    else:
        accion = "ninguna"

    if n_clases == 3:
        nivel = {"derivar": "Muy bajo", "reforzar_y_revaluar": "Bajo",
                 "ninguna": "Adecuado"}[accion]
    else:
        nivel = "En riesgo" if T <= corte_bajo else "Adecuado"

    return NivelResultado(
        T=round(float(T), 1),
        nivel=nivel,
        accion=accion,
        descriptor_verbal=descriptor_verbal(T),
        n_clases=n_clases,
    )


# --------------------------------------------------------------------------- #
# Criterio de niveles configurable (config.yaml > scoring > niveles)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Corte:
    nombre: str        # nivel que ve el docente ("Adecuado", "En riesgo", "Muy bajo"...)
    maximo: float      # el niño cae aquí si su puntuación <= maximo
    accion: str        # "ninguna" | "reforzar_y_revaluar" | "derivar"


@dataclass(frozen=True)
class CriterioNiveles:
    """De la PD y la edad al nivel del niño, con cortes y fuente declarados en config.yaml.

    base = "percentil": usa el percentil de la Tabla B.9 (dato publicado del manual).
    base = "T":         usa la T estimada desde el percentil (no publicada para esta escala).
    Los cortes van del peor nivel al mejor; el niño cae en el primero que alcance.
    Varios cortes pueden compartir nombre con distinta acción (p. ej. "En riesgo" con
    acción "derivar" por debajo de un segundo corte).
    """

    base: str
    cortes: tuple[Corte, ...]
    fuente: str = ""

    def __post_init__(self):
        if self.base not in ("percentil", "T"):
            raise ValueError(f"scoring.niveles.base debe ser 'percentil' o 'T', no {self.base}")
        maximos = [c.maximo for c in self.cortes]
        if not self.cortes or maximos != sorted(maximos):
            raise ValueError("scoring.niveles.cortes debe ir del peor nivel al mejor "
                             "(máximos crecientes)")

    @classmethod
    def de_config(cls, cfg) -> CriterioNiveles:
        n = cfg.get("scoring", "niveles", default=None)
        if n is None:   # compatibilidad con configuraciones antiguas (n_clases + cortes T)
            return cls.por_T(int(cfg.get("scoring", "n_clases", default=2)),
                             float(cfg.get("scoring", "corte_bajo_T", default=CORTE_BAJO)),
                             float(cfg.get("scoring", "corte_muy_bajo_T",
                                           default=CORTE_MUY_BAJO)))
        return cls(base=n["base"], fuente=n.get("fuente", ""),
                   cortes=tuple(Corte(c["nombre"], float(c["maximo"]), c["accion"])
                                for c in n["cortes"]))

    @classmethod
    def por_T(cls, n_clases: int = 2, corte_bajo: float = CORTE_BAJO,
              corte_muy_bajo: float = CORTE_MUY_BAJO) -> CriterioNiveles:
        """Equivalente al criterio histórico `nivel_desde_T`."""
        riesgo = "En riesgo" if n_clases == 2 else "Bajo"
        muy_bajo = "En riesgo" if n_clases == 2 else "Muy bajo"
        return cls("T", (Corte(muy_bajo, corte_muy_bajo, "derivar"),
                         Corte(riesgo, corte_bajo, "reforzar_y_revaluar"),
                         Corte("Adecuado", float("inf"), "ninguna")))

    @property
    def etiquetas(self) -> list[str]:
        """Niveles distintos del mejor al peor (orden ordinal para el kappa ponderado)."""
        vistos = []
        for c in reversed(self.cortes):
            if c.nombre not in vistos:
                vistos.append(c.nombre)
        return vistos

    def clasificar(self, pd_valor: int, edad_meses: int, baremo) -> NivelResultado:
        from grafomotor.scoring.baremo import pd_a_T

        r = pd_a_T(pd_valor, edad_meses, baremo)
        valor = r["percentil"] if self.base == "percentil" else r["T"]
        corte = next((c for c in self.cortes if valor <= c.maximo), self.cortes[-1])
        return NivelResultado(T=r["T"], nivel=corte.nombre, accion=corte.accion,
                              descriptor_verbal=descriptor_verbal(r["T"]),
                              n_clases=len(self.etiquetas), percentil=r["percentil"])

    def en_riesgo(self, pd_valor: int, edad_meses: int, baremo) -> bool:
        """Para el tamizaje: cualquier nivel que pida alguna acción."""
        return self.clasificar(pd_valor, edad_meses, baremo).accion != "ninguna"
