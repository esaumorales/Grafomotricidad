"""
Genera un DATASET SINTÉTICO completo para dejar el proyecto ejecutable de punta a punta
sin datos reales:

  data/raw/<child_id>/<figura_id>.jpg   "fotos" (plantilla perturbada sobre papel)
  data/labels/etiquetas.csv             edad, figura, puntaje 0/1, evaluador...

>>> Todo esto es de MENTIRA. Cuando tengas los datos reales:
      1) borra data/raw/* y data/labels/etiquetas.csv
      2) copia tus fotos a data/raw/<child_id>/<figura_id>.jpg
      3) rellena data/labels/etiquetas.csv (ver docs/DATOS.md)
      4) sustituye data/templates/*.png por las figuras reales del CUMANIN-2
      5) sustituye config/baremos.csv por la tabla oficial (teacorrige.com)

Uso:  python scripts/99_generar_datos_sinteticos.py --n-ninos 150 --seed 7
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

from grafomotor.augment.label_safe import deformacion_elastica
from grafomotor.config import load_config


def _perturbar(plantilla: np.ndarray, severidad: float, rng: np.random.Generator) -> np.ndarray:
    """severidad 0 (perfecta) .. 1 (muy mal). Aplica temblor, rotación, hueco, escala."""
    im = plantilla.copy()
    # temblor de trazo
    im = deformacion_elastica(im, alpha=4 + 20 * severidad, sigma=6)
    # rotación (criterio de error del CUMANIN-2)
    ang = float(rng.normal(0, 18 * severidad))
    M = cv2.getRotationMatrix2D((im.shape[1] / 2, im.shape[0] / 2), ang, 1.0)
    im = cv2.warpAffine(im, M, im.shape[::-1], flags=cv2.INTER_NEAREST)
    # distorsión de proporción
    fx = 1 + float(rng.normal(0, 0.25 * severidad))
    im = cv2.resize(im, None, fx=max(0.5, fx), fy=1.0, interpolation=cv2.INTER_NEAREST)
    im = cv2.resize(im, plantilla.shape[::-1], interpolation=cv2.INTER_NEAREST)
    # hueco (fallo de cierre)
    if rng.random() < severidad:
        ys, xs = np.where(im > 0)
        if len(xs):
            k = rng.integers(len(xs))
            cv2.circle(im, (int(xs[k]), int(ys[k])), int(8 + 20 * severidad), 0, -1)
    return im


def _a_foto(figura_bin: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Convierte la figura binaria en una 'foto' de hoja: papel claro, trazo oscuro, ruido."""
    H, W = 900, 700
    hoja = np.full((H, W), 235, np.uint8)
    hoja += rng.integers(-6, 6, (H, W), dtype=np.int16).clip(0, 255).astype(np.uint8) - 0
    fig = cv2.resize(figura_bin, (520, 520), interpolation=cv2.INTER_NEAREST)
    y0, x0 = (H - 520) // 2, (W - 520) // 2
    zona = hoja[y0:y0 + 520, x0:x0 + 520]
    zona[fig > 0] = rng.integers(20, 60)
    hoja[y0:y0 + 520, x0:x0 + 520] = zona
    ang = float(rng.normal(0, 2.5))
    M = cv2.getRotationMatrix2D((W / 2, H / 2), ang, 1.0)
    return cv2.warpAffine(hoja, M, (W, H), borderValue=235)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-ninos", type=int, default=150)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()

    cfg = load_config()
    tpl_dir = cfg.ruta("templates")
    raw_dir = cfg.ruta("raw")
    raw_dir.mkdir(parents=True, exist_ok=True)

    plantillas = {}
    for fid in cfg.figuras:
        p = tpl_dir / f"{fid}.png"
        if not p.exists():
            print(f"[ERROR] falta {p}. Corre antes: python scripts/gen_plantillas.py")
            return 1
        plantillas[fid] = (cv2.imread(str(p), cv2.IMREAD_GRAYSCALE) > 127).astype(np.uint8) * 255

    rng = np.random.default_rng(a.seed)
    figuras = list(cfg.figuras)
    filas = []
    for i in range(1, a.n_ninos + 1):
        cid = f"NINO_{i:04d}"
        edad = int(rng.integers(36, 72))                      # 3;0 .. 5;11
        # "habilidad" del niño: sesgada a población normal, peor cuanto más pequeño
        habilidad = float(np.clip(rng.beta(5, 2) - (60 - edad) / 120, 0.05, 0.98))
        (raw_dir / cid).mkdir(parents=True, exist_ok=True)
        for j, fid in enumerate(figuras):
            dif_figura = j / max(1, len(figuras) - 1) * 0.5   # figuras posteriores más difíciles
            severidad = float(np.clip(1 - habilidad + dif_figura + rng.normal(0, 0.08), 0, 1))
            fig = _perturbar(plantillas[fid], severidad, rng)
            foto = _a_foto(fig, rng)
            rel = f"raw/{cid}/{fid}.jpg"
            cv2.imwrite(str(raw_dir.parent / rel), foto, [cv2.IMWRITE_JPEG_QUALITY, 88])
            puntaje = int(severidad < 0.45)                   # etiqueta "del docente"
            filas.append({
                "child_id": cid, "edad_meses": edad, "sexo": rng.choice(["F", "M"]),
                "figura_id": fid, "imagen_path": rel, "puntaje": puntaje,
                "evaluador": rng.choice(["DOC_A", "DOC_B"]),
                "fecha": "2026-03-01", "version_baremo": "SINTETICO",
            })

    df = pd.DataFrame(filas)
    out = cfg.ruta("labels")
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(df.groupby("figura_id")["puntaje"].mean().round(2).to_string())
    print(f"\n{a.n_ninos} niños · {len(df)} imágenes  ->  {raw_dir}")
    print(f"etiquetas  ->  {out}")
    print("Tasa de acierto global:", round(df['puntaje'].mean(), 3),
          " · niños PD=0:", int((df.groupby('child_id')['puntaje'].sum() == 0).sum()))
    print("\n[RECORDATORIO] Datos sintéticos. Reemplázalos por los reales (ver cabecera).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
