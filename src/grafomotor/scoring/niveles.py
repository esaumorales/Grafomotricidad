"""
Nivel de desempeño grafomotor.

Forma recomendada: `CriterioNiveles` (cortes y fuente en config.yaml > scoring > niveles),
que clasifica sobre el PERCENTIL de la Tabla B.9 (pág. 83), el único dato confirmado contra
el libro físico. `nivel_desde_percentil` es la versión simple con los cortes por defecto.

Los cortes T>=41/31-40/<=30 que citaba una versión anterior (manual, pág. 98-99) NO están
verificados: el equipo no ha confirmado que esas páginas correspondan a esta edición del
manual ni a la subescala de Visopercepción (ver ESTADO.md). `nivel_desde_T` se conserva
solo como criterio histórico.

Cortes por defecto sobre el percentil (convención estándar en psicometría, ~ -1 y -2 DE):

    Pc > 16   -> Adecuado
    Pc 3-16   -> Bajo (en riesgo / screening)   [~ -1 DE]
    Pc <= 2   -> Muy bajo (derivar)              [~ -2 DE]

Si el equipo verifica las páginas 98-99 del manual original, estos cortes deben sustituirse
por los oficiales (documentando la fuente exacta en config.yaml).

`n_clases`:
  2 -> {Adecuado, En riesgo}
  3 -> {Adecuado, Bajo, Muy bajo}
"""
from __future__ import annotations

import math
from dataclasses import dataclass

CORTE_BAJO_PC = 16
CORTE_MUY_BAJO_PC = 2

# Bandas descriptivas por percentil (convención estándar en psicometría, equivalente
# aprox. a bandas de -2/-1/0/+1/+2 desviaciones típicas). NO provienen de una tabla del
# manual CUMANIN: son una convención general para el panel técnico del especialista.
_BANDAS_DESCRIPTIVAS = [
    ("Muy alto", 98, 100),
    ("Alto", 91, 97),
    ("Medio-alto", 75, 90),
    ("Medio", 25, 74),
    ("Medio-bajo", 9, 24),
    ("Bajo", 3, 8),
    ("Muy bajo", 0, 2),
]

# Criterio histórico por T (cortes sin verificar) y su tabla de descriptores.
CORTE_BAJO = 40
CORTE_MUY_BAJO = 30
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
    percentil: float | None
    nivel: str                 # etiqueta según los cortes / n_clases
    accion: str                # "ninguna" | "reforzar_y_revaluar" | "derivar"
    descriptor_verbal: str     # banda descriptiva (para el especialista)
    n_clases: int
    T: float | None = None     # solo en el criterio histórico por T


def descriptor_verbal(percentil: float) -> str:
    for nombre, lo, hi in _BANDAS_DESCRIPTIVAS:
        if lo <= percentil <= hi:
            return nombre
    return "Medio"


def descriptor_verbal_T(T: float) -> str:
    for nombre, lo, hi in TABLA_5_2:
        if lo <= T <= hi:
            return nombre
    return "Medio"


def nivel_desde_percentil(percentil: float, n_clases: int = 2,
                          corte_bajo: int = CORTE_BAJO_PC,
                          corte_muy_bajo: int = CORTE_MUY_BAJO_PC) -> NivelResultado:
    if percentil <= corte_muy_bajo:
        accion = "derivar"
    elif percentil <= corte_bajo:
        accion = "reforzar_y_revaluar"
    else:
        accion = "ninguna"

    if n_clases == 3:
        nivel = {"derivar": "Muy bajo", "reforzar_y_revaluar": "Bajo",
                 "ninguna": "Adecuado"}[accion]
    else:
        nivel = "En riesgo" if percentil <= corte_bajo else "Adecuado"

    return NivelResultado(
        percentil=round(float(percentil), 1),
        nivel=nivel,
        accion=accion,
        descriptor_verbal=descriptor_verbal(percentil),
        n_clases=n_clases,
    )


def nivel_desde_T(T: float, n_clases: int = 2, corte_bajo: int = CORTE_BAJO,
                  corte_muy_bajo: int = CORTE_MUY_BAJO) -> NivelResultado:
    """Criterio histórico (T estimada, cortes sin verificar). Preferir el de percentil."""
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
        percentil=None,
        nivel=nivel,
        accion=accion,
        descriptor_verbal=descriptor_verbal_T(T),
        n_clases=n_clases,
        T=round(float(T), 1),
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
    base = "T":         usa la T estimada desde el percentil (no publicada para esta escala;
                        exige una columna T en el baremo).
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
        if n is None:   # compatibilidad con configuraciones anteriores
            if cfg.get("scoring", "corte_bajo_pc", default=None) is not None:
                return cls.por_percentil(
                    int(cfg.get("scoring", "n_clases", default=2)),
                    float(cfg.get("scoring", "corte_bajo_pc", default=CORTE_BAJO_PC)),
                    float(cfg.get("scoring", "corte_muy_bajo_pc", default=CORTE_MUY_BAJO_PC)))
            return cls.por_T(int(cfg.get("scoring", "n_clases", default=2)),
                             float(cfg.get("scoring", "corte_bajo_T", default=CORTE_BAJO)),
                             float(cfg.get("scoring", "corte_muy_bajo_T",
                                           default=CORTE_MUY_BAJO)))
        return cls(base=n["base"], fuente=n.get("fuente", ""),
                   cortes=tuple(Corte(c["nombre"], float(c["maximo"]), c["accion"])
                                for c in n["cortes"]))

    @classmethod
    def por_percentil(cls, n_clases: int = 2, corte_bajo: float = CORTE_BAJO_PC,
                      corte_muy_bajo: float = CORTE_MUY_BAJO_PC) -> CriterioNiveles:
        """Equivalente a `nivel_desde_percentil`."""
        riesgo = "En riesgo" if n_clases == 2 else "Bajo"
        muy_bajo = "En riesgo" if n_clases == 2 else "Muy bajo"
        return cls("percentil", (Corte(muy_bajo, corte_muy_bajo, "derivar"),
                                 Corte(riesgo, corte_bajo, "reforzar_y_revaluar"),
                                 Corte("Adecuado", float("inf"), "ninguna")))

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
        if self.base == "T" and math.isnan(r["T"]):
            raise ValueError("scoring.niveles.base = 'T' exige una columna T en el baremo")
        valor = r["percentil"] if self.base == "percentil" else r["T"]
        corte = next((c for c in self.cortes if valor <= c.maximo), self.cortes[-1])
        # la T (si existe) es una estimación: el descriptor se da siempre por percentil
        T = None if math.isnan(r["T"]) else r["T"]
        return NivelResultado(percentil=r["percentil"], nivel=corte.nombre,
                              accion=corte.accion,
                              descriptor_verbal=descriptor_verbal(r["percentil"]),
                              n_clases=len(self.etiquetas), T=T)

    def en_riesgo(self, pd_valor: int, edad_meses: int, baremo) -> bool:
        """Para el tamizaje: cualquier nivel que pida alguna acción."""
        return self.clasificar(pd_valor, edad_meses, baremo).accion != "ninguna"
