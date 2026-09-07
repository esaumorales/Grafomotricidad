"""
Preprocesa las fotos de data/raw/ -> data/interim/ (figuras binarias registradas).

Guarda un PNG por (child_id, figura_id) y un CSV con avisos de calidad/registro.
"""
from __future__ import annotations

import sys

import cv2
import pandas as pd

from grafomotor.config import load_config
from grafomotor.io import cargar_etiquetas
from grafomotor.preprocessing import preprocesar_figura


def main() -> int:
    cfg = load_config()
    df = cargar_etiquetas(cfg.ruta("labels"))
    tpl_dir = cfg.ruta("templates")
    out_dir = cfg.ruta("interim")
    out_dir.mkdir(parents=True, exist_ok=True)
    pre_cfg = cfg.get("preprocesamiento", default={})

    filas = []
    for _, row in df.iterrows():
        fid = row["figura_id"]
        tpl_path = tpl_dir / f"{fid}.png"
        if not tpl_path.exists():
            filas.append({**row, "estado": "sin_plantilla"})
            continue
        tpl = (cv2.imread(str(tpl_path), cv2.IMREAD_GRAYSCALE) > 127).astype("uint8") * 255
        foto = cfg.ruta("raw") / row["imagen_path"].replace("raw/", "")
        if not foto.exists():
            filas.append({**row, "estado": "sin_foto"})
            continue
        res = preprocesar_figura(str(foto), tpl, pre_cfg)
        dst = out_dir / f"{row['child_id']}__{fid}.png"
        cv2.imwrite(str(dst), res.figura_bin)
        filas.append({
            "child_id": row["child_id"], "figura_id": fid, "interim_path": dst.name,
            "calidad": res.calidad, "registro_ok": res.registro_ok,
            "rotacion_deg": round(res.rotacion_deg, 1), "aviso": res.aviso or "",
        })

    rep = pd.DataFrame(filas)
    rep.to_csv(out_dir / "_preprocesamiento.csv", index=False)
    if "estado" in rep.columns:
        print("sin procesar:", rep["estado"].value_counts().to_dict())
    ok = rep[rep.get("interim_path").notna()] if "interim_path" in rep else rep.iloc[0:0]
    if len(ok):
        print(f"registro OK: {int(ok['registro_ok'].sum())}/{len(ok)}   "
              f"calidad media: {ok['calidad'].mean():.2f}")
        avisos = ok[ok["aviso"] != ""]["aviso"].value_counts().to_dict()
        if avisos:
            print("avisos:", avisos)
    print(f"\n{len(rep)} figuras -> {out_dir}  (detalle en _preprocesamiento.csv)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
