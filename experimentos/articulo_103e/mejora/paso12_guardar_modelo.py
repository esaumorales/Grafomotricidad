"""Guarda el modelo final del artículo (V0: Random Forest con indicadores generales + por criterio, sin
proporción) para la aplicación web, en dos versiones:
  modelo_rf_103e_83   entrenado con los 83 niños de desarrollo (para probar el sistema con los 20 apartados)
  modelo_rf_103e_103  entrenado con los 103 niños (uso real)
Mismo ajuste que paso4_prueba.py (búsqueda en malla por niño + corte por prevalencia). Cada carpeta lleva
modelo.joblib y manifiesto.json (columnas, punto de corte, límites de confianza, medidas de las plantillas).
Comprueba que la versión de 83 reproduce las probabilidades de prueba_V0_base.parquet y que
prediccion_final.py, partiendo de las imágenes procesadas, da las mismas probabilidades."""
import json
import sys
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn

from grafomotor.io import a_binaria, cargar_plantillas, leer_gris
from grafomotor.model.dataset import matriz
from paso3_evaluar import ajustar, cfg, construir_datos

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from criterios import medir  # noqa: E402
from prediccion_final import ModeloFinal  # noqa: E402

SAL = Path(__file__).resolve().parents[1] / "modelos"
d, C = construir_datos()
cols = C["base"]
lim = json.load(open("evaluacion_confianza_V0.json", encoding="utf-8"))["limites"]
ref = {f: {k: (None if v is None or (isinstance(v, float) and np.isnan(v)) else float(v))
           for k, v in medir(a_binaria(leer_gris(cfg.ruta("templates") / f"{f}.png"))).items()}
       for f in cfg.figuras}


def guardar(datos, nombre, descripcion):
    X, y = matriz(datos, cols), datos.puntaje.to_numpy().astype(int)
    m, corte, params = ajustar(X, y, datos.child_id.to_numpy(), datos.figura_id.to_numpy(), False)
    c = float(corte(np.array([0.5]), np.array(["F01"]))[0])
    carpeta = SAL / nombre; carpeta.mkdir(parents=True, exist_ok=True)
    joblib.dump(m, carpeta / "modelo.joblib")
    man = {"version": nombre, "descripcion": descripcion, "fecha": date.today().isoformat(),
           "n_ninos": int(datos.child_id.nunique()), "n_figuras": int(len(datos)),
           "feature_names": cols, "punto_de_corte": c,
           "limites_confianza": {"incorrecta_si_prob_menor_o_igual": lim["a_incorrecta"],
                                 "correcta_si_prob_mayor_o_igual": lim["b_correcta"]},
           "hiperparametros": {k: (None if v is None else v) for k, v in params.items()},
           "figuras": list(cfg.figuras), "criterios_plantilla": ref,
           "entrada": "figura binaria 512 px de preprocesar_figura (registro: traslación); ver prediccion_final.py",
           "versiones": {"python": sys.version.split()[0], "scikit-learn": sklearn.__version__}}
    (carpeta / "manifiesto.json").write_text(json.dumps(man, indent=2, ensure_ascii=False), encoding="utf-8")
    print(nombre, "corte", round(c, 4), params, flush=True)
    return m, c


dev = d[d.conjunto == "desarrollo"].reset_index(drop=True)
test = d[d.conjunto == "prueba"].reset_index(drop=True)
m83, c83 = guardar(dev, "modelo_rf_103e_83", "Entrenado con los 83 niños de desarrollo; los 20 apartados no se usaron.")
guardar(d, "modelo_rf_103e_103", "Entrenado con los 103 niños (uso real en la aplicación).")

# comprobación 1: reproduce las probabilidades de la prueba única
p = m83.predict_proba(matriz(test, cols))[:, 1]
ref_prueba = pd.read_parquet("prueba_V0_base.parquet")
t = test[["child_id", "figura_id"]].assign(p=p).merge(ref_prueba, on=["child_id", "figura_id"])
print("comprobación 1, máx. diferencia con prueba_V0_base:", float(np.abs(t.p - t.prob).max()))

# comprobación 2: prediccion_final.py desde las imágenes procesadas (5 niños de prueba)
mf = ModeloFinal(SAL / "modelo_rf_103e_83")
plantillas = cargar_plantillas(cfg)
interim = Path(cfg.ruta("interim")); dif = []
for r in t[t.child_id.isin(t.child_id.unique()[:5])].itertuples():
    b = a_binaria(leer_gris(interim / f"{r.child_id}__{r.figura_id}.png"))
    dif.append(abs(mf.probabilidad(b, r.figura_id, plantillas[r.figura_id], cfg.figuras[r.figura_id]) - r.p))
print("comprobación 2, máx. diferencia desde la imagen:", float(max(dif)), "en", len(dif), "figuras")
