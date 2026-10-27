"""Etiquetas por mayoría con todas las revisiones a ciegas hechas hasta ahora (lotes 1 y 2).

Votos de cada figura: la nota original del equipo + la de cada revisor (sin las marcadas como dudosas).
Etiqueta final: la mayoría; si hay empate, la de José (revisó todo el lote 1); si José no la revisó,
se conserva la original. Acuerdo entre personas: porcentaje y kappa en las figuras en común.
Uso: python paso10_etiquetas_mayoria.py <estado_servidor.json>"""
import json
import sys
from itertools import combinations
from pathlib import Path

import pandas as pd
from sklearn.metrics import cohen_kappa_score

AQUI = Path(__file__).parent
e = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
items = {i["id"]: i for i in json.loads(Path("D:/Calificador_Grafomotor/revision.json").read_text(encoding="utf-8"))["items"]}
orig = pd.read_csv("D:/Datos niños/Experimento_103c/etiquetas.csv")
clave = orig.set_index(["child_id", "figura_id"])["puntaje"]

filas = []
for u, resp in e.get("revision", {}).items():
    for rid, r in resp.items():
        it = items[rid]
        if r.get("p") in (0, 1) and not r.get("dud"):
            filas.append({"rid": rid, "lote": it["lote"], "child_id": it["nino"], "figura_id": it["fig"], "usuario": u, "nota": int(r["p"])})
r = pd.DataFrame(filas)
ancho = r.pivot_table(index=["child_id", "figura_id", "lote"], columns="usuario", values="nota", aggfunc="first").reset_index()
ancho["original"] = [int(clave[(c, f)]) for c, f in zip(ancho.child_id, ancho.figura_id)]
rev = sorted(r.usuario.unique())

print("respuestas válidas por persona y lote:")
print(r.groupby(["usuario", "lote"]).size().unstack(fill_value=0).to_string())
print("\nacuerdo entre personas (figuras en común):")
for a, b in combinations(rev + ["original"], 2):
    x = ancho[[a, b]].dropna()
    if len(x) >= 20:
        print(f"  {a:8s} - {b:8s}: {len(x):4d} figuras | coinciden {100 * (x[a] == x[b]).mean():.1f} % | kappa {cohen_kappa_score(x[a].astype(int), x[b].astype(int)):.3f}")


def final(f):
    votos = [f[u] for u in rev + ["original"] if pd.notna(f[u])]
    unos = sum(votos)
    if unos * 2 > len(votos):
        return 1
    if unos * 2 < len(votos):
        return 0
    return int(f["jose"]) if "jose" in f and pd.notna(f["jose"]) else int(f["original"])


ancho["n_revisores"] = ancho[rev].notna().sum(axis=1)
ancho["final"] = ancho.apply(final, axis=1)
print("\nfiguras revisadas:", len(ancho), "| por número de revisores:", ancho.n_revisores.value_counts().sort_index().to_dict())
cambios = ancho[ancho.final != ancho.original]
print("notas que cambian:", len(cambios), "| 0→1:", int((cambios.final == 1).sum()), "| 1→0:", int((cambios.final == 0).sum()))
print("cambios por lote:", cambios.groupby("lote").size().to_dict())
print("cambios por figura:", cambios.groupby("figura_id").size().to_dict())

nuevo = ancho.set_index(["child_id", "figura_id"])["final"]
et = orig.copy()
et["puntaje"] = [int(nuevo.get((c, f), p)) for c, f, p in zip(et.child_id, et.figura_id, et.puntaje)]
destino = AQUI.parent / "etiquetas.csv"
et.to_csv(destino, index=False)
ancho.to_csv(AQUI / "votos_por_figura.csv", index=False)
print("guardado:", destino, "| cambiadas frente a la original:", int((et.puntaje != orig.puntaje).sum()))
