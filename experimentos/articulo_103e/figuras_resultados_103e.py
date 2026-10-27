"""Figuras de resultados del artículo con los datos reales (Experimento_103e, 103 niños, 1,545 figuras).
Mismo estilo que las figuras de práctica (Figuras/Resultados_provisionales/figuras_resultados.py), pero
sin kappa: exactitud balanceada (EB) por figura e ICC de la PD, como en el artículo.
- Valores e IC 95 % de los seis modelos: resultados_sin_kappa.json (resumen_sin_kappa.py).
- EB por figura, Bland-Altman y ablación: predicciones fuera de pliegue de processed/; los IC de la
  ablación salen de un bootstrap por niño (2000 réplicas, misma semilla que el resumen).
Colores validados (validate_palette.js, modo claro): ML azul #2a78d6 (círculo), DL naranja #eb6834
(cuadrado); la forma del marcador repite la familia para impresión en gris.
Uso: python figuras_resultados_103e.py <carpeta de salida>"""
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score

from grafomotor.evaluation.metrics import icc_acuerdo_absoluto

AQUI = Path(__file__).parent
P = AQUI / "processed"
SAL = Path(sys.argv[1]); SAL.mkdir(parents=True, exist_ok=True)
RES = json.load(open(AQUI / "resultados_sin_kappa.json", encoding="utf-8"))
plt.rcParams.update({"font.family": ["Arial", "DejaVu Sans"], "font.size": 9, "axes.edgecolor": "#c3c2b7",
                     "axes.labelcolor": "#0b0b0b", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "axes.spines.top": False, "axes.spines.right": False})
ML, DL, TINTA, GRIS, REJILLA = "#2a78d6", "#eb6834", "#0b0b0b", "#898781", "#e1e0d9"
MODELOS = [  # (nombre, archivo oof, familia)
    ("Regresión logística", "oof_crit_con_criterios_sin_proporcion_reg_logistica", "ML"),
    ("Random Forest", "oof_crit_con_criterios_sin_proporcion_random_forest", "ML"),
    ("XGBoost", "oof_crit_con_criterios_sin_proporcion_xgboost", "ML"),
    ("ResNet-18", "oof_dl_resnet18_corte", "DL"),
    ("MobileNetV2", "oof_dl_mobilenetv2_corte", "DL"),
    ("EfficientNet-B0", "oof_dl_efficientnet_b0_corte", "DL"),
]
# nombres de config.yaml > figuras (escala de Visopercepción del CUMANIN)
NOMBRES_FIG = ["Línea recta", "Dos líneas horizontales", "Cruz", "Círculo", "Cuadrado", "Triángulo", "Aspa",
               "Línea ondulada", "Rectángulo con aspa", "Rombo", "Círculo y triángulo", "U", "Lazo",
               "Doble pico ondulado", "Cuadrado y círculo"]
B, SEM = 2000, 20260930


def cargar(arch):
    return pd.read_parquet(P / f"{arch}.parquet").sort_values(["child_id", "figura_id"]).reset_index(drop=True)


def guardar(fig, nombre):
    for ext, kw in (("png", {}), ("tif", {"pil_kwargs": {"compression": "tiff_lzw"}}), ("pdf", {})):
        fig.savefig(SAL / f"{nombre}.{ext}", dpi=400, bbox_inches="tight", facecolor="white", **kw)
    plt.close(fig)


def bandas(ax, cortes, etiquetas):
    for c in cortes:
        ax.axvline(c, color=REJILLA, lw=1, zorder=0)
    for x, t in etiquetas:
        ax.text(x, 1.01, t, transform=ax.get_xaxis_transform(), ha="center", va="bottom",
                fontsize=7 if len(t) > 7 else 7.5, color=GRIS)


def num(v, signo=False):
    """Número con 2 decimales y signo menos tipográfico."""
    t = f"{v:+.2f}" if signo else f"{v:.2f}"
    return t.replace("-", "−")


def eb_cci_ic(o):
    """EB por figura e ICC de la PD con IC 95 % (bootstrap por niño, niños repetidos como niños distintos)."""
    rng = np.random.default_rng(SEM)
    ninos = o.child_id.unique(); idx = {c: np.where(o.child_id == c)[0] for c in ninos}
    pdn = o.groupby("child_id").agg(r=("y", "sum"), p=("yhat", "sum"))
    e0, c0 = balanced_accuracy_score(o.y, o.yhat), icc_acuerdo_absoluto(pdn.r, pdn.p)
    es, cs = [], []
    for _ in range(B):
        sel = rng.choice(ninos, len(ninos)); ii = np.concatenate([idx[c] for c in sel])
        es.append(balanced_accuracy_score(o.y.values[ii], o.yhat.values[ii]))
        cs.append(icc_acuerdo_absoluto(pdn.r.loc[sel].values, pdn.p.loc[sel].values))
    return {"eb": e0, "eb_ic": np.percentile(es, [2.5, 97.5]), "cci": c0, "cci_ic": np.percentile(cs, [2.5, 97.5])}


# ---------- Figura 5: comparación de los seis modelos (EB por figura e ICC de la PD) ----------
res = {}
for n, _, f in MODELOS:
    m = RES["modelos"][n]
    res[n] = {"eb": m["exactitud_balanceada"], "eb_ic": m["exactitud_balanceada_IC95"],
              "cci": m["cci_PD"], "cci_ic": m["cci_PD_IC95"]}
pd.DataFrame([{"modelo": n, "familia": f, "EB": r["eb"], "EB_li": r["eb_ic"][0], "EB_ls": r["eb_ic"][1],
               "ICC_PD": r["cci"], "ICC_li": r["cci_ic"][0], "ICC_ls": r["cci_ic"][1]}
              for (n, _, f), r in zip(MODELOS, res.values())]).to_csv(SAL / "datos_figura_modelos.csv", index=False)
fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=True)
ys = np.arange(len(MODELOS))[::-1]
for ax, clave, titulo, lim, cortes, etq in (
        (axs[0], "eb", "a) Exactitud balanceada por figura", (0.5, 1.0), [0.70, 0.80],
         [(0.60, "bajo"), (0.75, "medio"), (0.90, "alto")]),
        (axs[1], "cci", "b) ICC de la puntuación directa", (0.3, 1.0), [0.5, 0.75, 0.9],
         [(0.40, "bajo"), (0.625, "medio"), (0.825, "alto"), (0.95, "excelente")])):
    bandas(ax, cortes, etq)
    for y, (n, _, f) in zip(ys, MODELOS):
        r = res[n]; col = ML if f == "ML" else DL
        li, ls = r[f"{clave}_ic"]
        ax.plot([li, ls], [y, y], color=col, lw=2, solid_capstyle="round")
        ax.plot(r[clave], y, "o" if f == "ML" else "s", ms=7, color=col, mec="white", mew=1.5, zorder=3)
        ax.text(ls + 0.012, y, f"{r[clave]:.3f}", va="center", fontsize=8, color=TINTA)
    ax.set_xlim(*lim); ax.set_title(titulo, loc="left", fontsize=9.5, pad=14)
    ax.tick_params(length=0)
axs[0].set_yticks(ys, [n for n, _, _ in MODELOS])
axs[0].plot([], [], "o", color=ML, label="Aprendizaje automático (ML)")
axs[0].plot([], [], "s", color=DL, label="Aprendizaje profundo (DL)")
fig.legend(loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.55, -0.1))
guardar(fig, "Figura5_modelos")

# ---------- Figura 6: Bland-Altman del mejor modelo de cada familia ----------
mejor_dl = max((m for m in MODELOS if m[2] == "DL"), key=lambda m: res[m[0]]["eb"])
fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=True)
for ax, (n, a, f), letra in zip(axs, [MODELOS[1], mejor_dl], "ab"):
    o = cargar(a); pdn = o.groupby("child_id").agg(r=("y", "sum"), p=("yhat", "sum"))
    media, dif = (pdn.r + pdn.p) / 2, pdn.p - pdn.r
    sesgo, de = dif.mean(), dif.std(ddof=1); li, ls = sesgo - 1.96 * de, sesgo + 1.96 * de
    cuenta = pd.DataFrame({"m": media, "d": dif}).value_counts().reset_index(name="n")
    col = ML if f == "ML" else DL
    ax.axhline(0, color="#c3c2b7", lw=1, zorder=0)
    ax.scatter(cuenta.m, cuenta.d, s=18 + 22 * (cuenta.n - 1), color=col, alpha=0.85,
               marker="o" if f == "ML" else "s", edgecolor="white", linewidth=1, zorder=3)
    ax.axhline(sesgo, color=TINTA, lw=1.2)
    for v in (li, ls):
        ax.axhline(v, color=TINTA, lw=1, ls=(0, (4, 3)))
    ax.text(15.3, sesgo, f"sesgo {num(sesgo, True)}", va="center", fontsize=7.5, color=TINTA)
    ax.text(15.3, ls, f"+1.96 DE {num(ls, True)}", va="center", fontsize=7.5, color="#52514e")
    ax.text(15.3, li, f"−1.96 DE {num(li, True)}", va="center", fontsize=7.5, color="#52514e")
    ax.set_xlim(0, 15); ax.set_title(f"{letra}) {n} ({f})", loc="left", fontsize=9.5)
    ax.set_xlabel("Media de la PD (modelo y referencia)")
    ax.grid(axis="y", color=REJILLA, lw=0.6); ax.set_axisbelow(True); ax.tick_params(length=0)
axs[0].set_ylabel("Diferencia de PD (modelo − referencia)")
fig.text(0.5, -0.06, "El tamaño del punto indica cuántos niños comparten la misma posición.",
         ha="center", fontsize=7.5, color=GRIS)
fig.subplots_adjust(wspace=0.45)
guardar(fig, "Figura6_bland_altman")

# ---------- Figura 8: EB en cada figura, mejor modelo de cada familia ----------
fig, ax = plt.subplots(figsize=(6.0, 4.6))
filas = []
for n, a, f in [MODELOS[1], mejor_dl]:
    o = cargar(a)
    for i in range(15):
        g = o[o.figura_id == f"F{i + 1:02d}"]
        filas.append({"modelo": n, "familia": f, "figura": i + 1, "EB": balanced_accuracy_score(g.y, g.yhat),
                      "pct_correctas": g.y.mean()})
kf = pd.DataFrame(filas); kf.round(3).to_csv(SAL / "datos_figura_eb_por_figura.csv", index=False)
ys = np.arange(15)[::-1]
bandas(ax, [0.70, 0.80], [(0.60, "bajo"), (0.75, "medio"), (0.90, "alto")])
for i, y in enumerate(ys):
    a, b = (kf[(kf.figura == i + 1) & (kf.familia == fam)].EB.iloc[0] for fam in ("ML", "DL"))
    ax.plot([a, b], [y, y], color=REJILLA, lw=2, zorder=1)
for fam, mk, off in (("ML", "o", 0.14), ("DL", "s", -0.14)):  # desplazados para que no se tapen
    d = kf[kf.familia == fam]
    ax.plot(d.EB, ys[d.figura - 1] + off, mk, ms=6.5, color=ML if fam == "ML" else DL,
            mec="white", mew=1.2, zorder=3, ls="none", label=f"{d.modelo.iloc[0]} ({fam})")
ax.set_yticks(ys, [f"{i + 1}. {t}" for i, t in enumerate(NOMBRES_FIG)])
ax.set_xlim(0.4, 1.0); ax.set_xlabel("Exactitud balanceada en cada figura"); ax.tick_params(length=0)
ax.legend(loc="lower right", frameon=False, fontsize=8)
guardar(fig, "Figura8_eb_por_figura")

# ---------- Figura 7: ablación (Random Forest) ----------
VERS = [("Indicadores generales", "oof_crit_antes_random_forest"),
        ("+ criterios del manual", "oof_crit_con_criterios_random_forest"),
        ("+ criterios, sin proporción", "oof_crit_con_criterios_sin_proporcion_random_forest")]
ra = {n: eb_cci_ic(cargar(a)) for n, a in VERS}
pd.DataFrame([{"version": n, "EB": r["eb"], "EB_li": r["eb_ic"][0], "EB_ls": r["eb_ic"][1],
               "ICC_PD": r["cci"], "ICC_li": r["cci_ic"][0], "ICC_ls": r["cci_ic"][1]}
              for n, r in ra.items()]).round(3).to_csv(SAL / "datos_figura_ablacion.csv", index=False)
fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.2), sharey=True)
ys = np.arange(3)[::-1]
for ax, clave, tit, lim in ((axs[0], "eb", "a) Exactitud balanceada por figura", (0.5, 1.0)),
                           (axs[1], "cci", "b) ICC de la puntuación directa", (0.3, 1.0))):
    for y, (n, _) in zip(ys, VERS):
        r = ra[n]; li, ls = r[f"{clave}_ic"]
        ax.plot([li, ls], [y, y], color=ML, lw=2, solid_capstyle="round")
        ax.plot(r[clave], y, "o", ms=7, color=ML, mec="white", mew=1.5, zorder=3)
        ax.text(ls + 0.012, y, f"{r[clave]:.3f}", va="center", fontsize=8, color=TINTA)
    ax.set_xlim(*lim); ax.set_title(tit, loc="left", fontsize=9.5); ax.tick_params(length=0)
    ax.grid(axis="x", color=REJILLA, lw=0.6); ax.set_axisbelow(True)
axs[0].set_yticks(ys, [n for n, _ in VERS])
guardar(fig, "Figura7_ablacion")
print(pd.read_csv(SAL / "datos_figura_modelos.csv").to_string())
print(pd.read_csv(SAL / "datos_figura_ablacion.csv").to_string())
print("mejor DL:", mejor_dl[0])
