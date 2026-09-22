"""
El test más importante: el informe para el docente debe ser entendible.
  - sin jerga técnica
  - con encabezado de resultado
  - con sugerencias cuando hay dificultades
  - frases razonablemente cortas
"""
import numpy as np

from grafomotor.explain import construir_informe, explicar_para_docente
from grafomotor.explain.plain_language import contiene_jerga
from grafomotor.model.predict import PrediccionFigura, agregar_sesion
from grafomotor.scoring.niveles import nivel_desde_percentil

FIGURAS = {"F01": "círculo", "F02": "cruz", "F03": "cuadrado",
           "F04": "triángulo", "F05": "cruz oblicua", "F06": "rombo"}
EXP_CFG = {"umbral_relevancia_shap": .03, "max_fortalezas": 2,
          "max_dificultades": 3, "umbral_confianza_baja": .6}


def _sesion(base: float):
    rng = np.random.default_rng(1)
    preds = []
    for fid in FIGURAS:
        ind = {k: float(np.clip(base + rng.normal(0, .05), 0, 1)) for k in
               ["precision_modelo", "vertices", "error_angular",
                "cierre", "intersecciones", "proporcion"]}
        ind["cierre"] = max(0.0, base - 0.3)          # debilidad clara
        ind["error_angular"] = max(0.0, base - 0.2)
        prob = float(np.clip(np.mean(list(ind.values())), .05, .95))
        preds.append(PrediccionFigura(fid, int(prob >= .5), round(prob, 3), ind))
    return agregar_sesion("NINO_TEST", 40, preds)


def _shap_con_debilidad_en_cierre():
    agg = {"precision_modelo": .02, "vertices": .03, "error_angular": -.05,
           "cierre": -.12, "intersecciones": .01, "proporcion": -.02}
    return {"agg_signed": agg, "agg_abs": {k: abs(v) for k, v in agg.items()},
            "por_figura": [agg] * 6, "base_value": 0.0}


def _informe(base, percentil):
    exp = explicar_para_docente(_sesion(base), nivel_desde_percentil(percentil, 2),
                                _shap_con_debilidad_en_cierre(), FIGURAS, EXP_CFG, "Ana")
    return construir_informe(exp)


def test_sin_jerga_tecnica():
    inf = _informe(0.45, 10)
    assert inf.alertas_estilo == [], f"jerga en el informe: {inf.alertas_estilo}"
    assert not contiene_jerga(inf.informe_docente_md)


def test_tiene_encabezado_y_sugerencias():
    inf = _informe(0.45, 10)
    md = inf.informe_docente_md
    assert "prestar atención" in md.lower() or "derivar" in md.lower()
    assert "Qué puedes hacer en el aula" in md
    assert "Cierre de las figuras" in md          # nombró la dificultad principal


def test_caso_adecuado_no_alarma():
    inf = _informe(0.9, 60)
    md = inf.informe_docente_md.lower()
    assert "adecuado para su edad" in md
    assert "derivar" not in md


def test_frases_cortas():
    inf = _informe(0.45, 10)
    largas = [s for s in inf.informe_docente_md.replace("\n", " ").split(". ")
              if len(s.split()) > 35]
    assert not largas, f"frases demasiado largas: {largas}"


def test_panel_tecnico_separado():
    inf = _informe(0.45, 10)
    # las cifras técnicas viven SOLO en el panel, no en el texto del docente
    assert "percentil" in inf.panel_tecnico["resumen"]
    assert str(inf.panel_tecnico["resumen"]["percentil"]) not in inf.informe_docente_md
