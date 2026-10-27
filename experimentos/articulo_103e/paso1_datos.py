"""Paso 1 (muestra final de 103 niños): recortes, participantes y etiquetas.

- Recorta cada figura de la hoja enderezada del calificador con el recuadro final que dejó el
  equipo (o el recuadro por defecto si no se movió) y la normaliza con la función del proyecto.
  Salida: D:/Proyecto Grafomotricidad - Tesis/data/raw_final/<niño>/F01..F15.jpg
- participantes_103.csv: edad en meses (si hay fecha de nacimiento), edad en años y sexo.
- etiquetas.csv: notas del evaluador "Equipo" (no se usan las de "IA-Claude").
  edad_meses: real si existe; si no, aproximada por la edad en años (4->54, 5->66, 6->75) solo
  para que el esquema la acepte; el nivel se evalúa aparte solo con los niños con edad real."""
import csv, json, re, sys
from pathlib import Path
import cv2, openpyxl

PROY = Path("D:/Proyecto Grafomotricidad - Tesis")
from grafomotor.preprocessing.hoja import normalizar_celda

AQUI = Path(__file__).parent
REN = Path("D:/Respaldos_Grafomotor/render_24-10")
HOJAS = Path("D:/Calificador_Grafomotor/datos/hojas")
SALIDA = PROY / "data/raw_final"

estado = json.loads((REN / "estado.json").read_text(encoding="utf-8"))
indice = json.loads((REN / "indice.json").read_text(encoding="utf-8"))["ninos"]
equipo = estado["punt"]["Equipo"]

# 1) recortes
n_rec = n_def = 0
for n in indice:
    (SALIDA / n["id"]).mkdir(parents=True, exist_ok=True)
    for pg in n["paginas"]:
        hoja = cv2.imread(str(HOJAS / pg["archivo"]), 0)
        alto, ancho = hoja.shape
        assert (ancho, alto) == (pg["ancho"], pg["alto"]), pg["archivo"]
        for f in pg["figuras"]:
            caja = estado["cajas"].get(f"{n['id']}|{f['id']}")
            if caja is None:
                caja, n_def = f["caja"], n_def + 1
            x0, y0, x1, y1 = (int(round(v)) for v in caja)
            x0, x1 = sorted((max(0, min(ancho, x0)), max(0, min(ancho, x1))))
            y0, y1 = sorted((max(0, min(alto, y0)), max(0, min(alto, y1))))
            cv2.imwrite(str(SALIDA / n["id"] / f"{f['id']}.jpg"), normalizar_celda(hoja[y0:y1, x0:x1]),
                        [cv2.IMWRITE_JPEG_QUALITY, 95])
            n_rec += 1
print(f"recortes: {n_rec} ({n_def} con el recuadro por defecto) -> {SALIDA}")

# 2) participantes
ws = openpyxl.load_workbook(PROY / "data/hojas_reales/calificacion_46_ninos.xlsx", data_only=True)["Calificación"]
excel = {r[0]: r for r in ws.iter_rows(min_row=3, values_only=True) if r[0]}
lote4 = {r["child_id"]: r for r in csv.DictReader(open(PROY / "data/hojas_reales/lote4_edad_sexo.csv", encoding="utf-8"))}
sexo_v = {r["child_id"]: r["sexo"] for r in csv.DictReader(open(PROY / "data/hojas_reales/sexo_ninos_antiguos.csv", encoding="utf-8"))}
APROX = {4: 54, 5: 66, 6: 75}
filas = []
for n in indice:
    c = n["id"]
    meses, anios, sexo, fuente = None, None, "", ""
    if c in lote4:
        r = lote4[c]
        meses = int(r["edad_meses"]) if r["edad_meses"] else None
        anios = int(r["edad_anios_cumplidos"]) if r["edad_anios_cumplidos"] else None
        sexo, fuente = r["sexo"], "lista de matrícula (lote 4)"
    else:
        r = excel[c]
        if r[1] not in (None, ""):
            meses, fuente = int(r[1]), "fecha de nacimiento"
            anios = meses // 12
        else:
            m = re.search(r"(\d) a", str(r[23] or ""))
            anios, fuente = (int(m.group(1)) if m else None), "edad en años de la ficha"
        sexo = sexo_v.get(c) or (r[2] or "")
    filas.append({"child_id": c, "edad_meses": meses, "edad_anios": anios, "sexo": sexo, "fuente_edad": fuente,
                  "edad_meses_modelo": meses if meses is not None else APROX.get(anios, 66)})
with open(AQUI / "participantes_103.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(filas[0])); w.writeheader(); w.writerows(filas)

# 3) etiquetas
par = {f["child_id"]: f for f in filas}
with open(AQUI / "etiquetas.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["child_id", "edad_meses", "figura_id", "imagen_path", "puntaje", "evaluador", "fecha", "sexo"])
    for n in indice:
        for k in range(1, 16):
            fid = f"F{k:02d}"
            w.writerow([n["id"], par[n["id"]]["edad_meses_modelo"], fid, f"raw_final/{n['id']}/{fid}.jpg",
                        equipo[n["id"]][fid]["p"], "Equipo", "", par[n["id"]]["sexo"]])
con_meses = sum(f["edad_meses"] is not None for f in filas)
print(f"participantes: {len(filas)} · con edad en meses: {con_meses} · sin edad: "
      f"{[f['child_id'] for f in filas if f['edad_anios'] is None]}")
