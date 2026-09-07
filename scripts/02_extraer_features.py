"""data/interim/ -> data/processed/features.parquet (6 indicadores por figura)."""
from __future__ import annotations

import sys

import cv2
import pandas as pd

from grafomotor.config import load_config
from grafomotor.features.extract import extraer_indicadores


def main() -> int:
    cfg = load_config()
    interim = cfg.ruta("interim")
    tpl_dir = cfg.ruta("templates")
    figuras_meta = cfg.figuras

    filas = []
    for png in sorted(interim.glob("*__*.png")):
        child_id, fid = png.stem.split("__")
        tpl_path = tpl_dir / f"{fid}.png"
        if not tpl_path.exists():
            continue
        fig = (cv2.imread(str(png), cv2.IMREAD_GRAYSCALE) > 127).astype("uint8") * 255
        tpl = (cv2.imread(str(tpl_path), cv2.IMREAD_GRAYSCALE) > 127).astype("uint8") * 255
        vec = extraer_indicadores(fig, tpl, fid, figuras_meta.get(fid, {}))
        filas.append({
            "child_id": child_id, "figura_id": fid,
            **vec.valores,
            **{f"raw_{k}": v for k, v in vec.raw.items()},
        })

    df = pd.DataFrame(filas)
    out = cfg.ruta("processed") / "features.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    print(df.head().to_string(index=False))
    print(f"\n{len(df)} filas -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
