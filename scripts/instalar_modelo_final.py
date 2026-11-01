"""Deja una versión del modelo final lista para la aplicación web, en models/final/<versión>/.

    python scripts/instalar_modelo_final.py --modelos <1_modelo> --plantillas <templates_cumanin> \
        --config-experimento <config_103e.yaml>

Copia cada versión (modelo.joblib + manifiesto.json), le añade las plantillas con que se midió el
entrenamiento (`plantillas/`) y guarda en su manifiesto las medidas esperadas de cada figura
(`figuras_meta`: vértices e intersecciones), que NO son las de config/config.yaml. Así la carpeta es autónoma.
"""
import argparse
import json
import shutil
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelos", required=True, help="carpeta con modelo_rf_103e_83 y modelo_rf_103e_103")
    ap.add_argument("--plantillas", required=True, help="carpeta con F01.png ... F15.png del experimento")
    ap.add_argument("--config-experimento", required=True, help="config_103e.yaml (sección figuras)")
    ap.add_argument("--destino", default=str(REPO / "models" / "final"))
    a = ap.parse_args()

    figuras = yaml.safe_load(Path(a.config_experimento).read_text(encoding="utf-8"))["figuras"]
    meta = {f: {"vertices_esperados": v["vertices_esperados"],
                "intersecciones_esperadas": v["intersecciones_esperadas"]} for f, v in figuras.items()}
    for origen in sorted(p for p in Path(a.modelos).iterdir() if (p / "modelo.joblib").exists()):
        dest = Path(a.destino) / origen.name
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origen / "modelo.joblib", dest / "modelo.joblib")
        (dest / "plantillas").mkdir(exist_ok=True)
        for f in meta:
            shutil.copy2(Path(a.plantillas) / f"{f}.png", dest / "plantillas" / f"{f}.png")
        man = json.loads((origen / "manifiesto.json").read_text(encoding="utf-8"))
        man["figuras_meta"] = meta
        (dest / "manifiesto.json").write_text(json.dumps(man, indent=2, ensure_ascii=False), encoding="utf-8")
        print("instalado:", dest)


if __name__ == "__main__":
    main()
