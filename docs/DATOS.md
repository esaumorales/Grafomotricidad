# Datos: carpetas, esquema de etiquetas y baremo

## Carpetas (todo bajo `data/`, ignoradas por git)

```
data/
├── raw/            fotos originales:  raw/<child_id>/<figura_id>.jpg
├── interim/        modelo A: figuras binarias registradas <child_id>__<figura_id>.png
├── interim_dl/     modelo B: recortes 224×224 en gris <child_id>__<figura_id>.png
├── processed/      features.parquet, particiones.csv, oof_*.parquet, evaluacion_*.json,
│                   comparacion_*, robustez_*, gradcam_*, practicidad_*
├── templates/      plantilla de referencia por figura: <figura_id>.png (binaria)
└── labels/
    ├── etiquetas.csv   (copiar de etiquetas_ejemplo.csv y rellenar)
    └── fotos_aula.csv  (opcional) 2.ª foto de la misma hoja en condiciones de aula
```

## `labels/etiquetas.csv`

| columna | oblig. | descripción |
|---|---|---|
| `child_id` | sí | código anónimo del niño/a (p. ej. `NINO_0007`) |
| `edad_meses` | sí | edad en meses el día de la prueba. **36–71** (3;0–5;11) |
| `figura_id` | sí | id de la figura (`F01`…), coherente con `config.yaml > figuras` |
| `imagen_path` | sí | ruta de la foto relativa a `data/` (`raw/NINO_0007/F03.jpg`) |
| `puntaje` | sí | **0 / 1** — corrección del **evaluador experto (el equipo)**, no de la docente, según los criterios del Apéndice C del CUMANIN original |
| `sexo` | no | `F` / `M` (la Tabla B.9 no distingue sexo) |
| `evaluador` | no | código del evaluador (para acuerdo inter‑evaluador) |
| `fecha` | no | ISO `AAAA‑MM‑DD` |
| `version_baremo` | no | versión exacta usada (p. ej. `CUMANIN_2002_TablaB9`) |
| `fecha_nacimiento` | no | de la hoja de registro (ISO) |
| `hora_inicio`, `hora_termino` | no | de la hoja de registro (`HH:MM`) |
| `mano` | no | mano usada: `derecha` / `izquierda` |

Se guardan **las 15 puntuaciones** de cada niño aunque en la aplicación grupal no se aplique
la regla de parada: el análisis calcula la PD completa y la PD del manual (parar tras 4
fallos seguidos) a partir de ellas (`scoring/pd.py`).

## `labels/fotos_aula.csv` (doble foto, opcional)

Si cada hoja se fotografía dos veces (una **controlada**: buena luz, hoja plana, celular en
soporte o escáner; otra **de aula**: a mano, luz del salón), `etiquetas.csv` apunta a la
controlada y este archivo a la de aula. La etiqueta se toma de `etiquetas.csv`.

| columna | descripción |
|---|---|
| `child_id`, `figura_id` | igual que en `etiquetas.csv` |
| `imagen_path` | ruta de la foto de aula relativa a `data/` (p. ej. `raw_aula/NINO_0007/F03.jpg`) |

`10_robustez.py` evalúa A y B sobre estas fotos. Sin ellas, la robustez solo se estima con
degradaciones sintéticas (evidencia más débil).

Una fila por **(niño, figura)**. `00_validar_datos.py` comprueba rango de edad,
duplicados y valores de `puntaje`, y avisa de desbalance / efecto suelo.

## `config/baremos.csv` (PD → Pc)

Fuente real: **Tabla B.9 "Escala de Visopercepción"**, manual **CUMANIN original**
(Portellano Pérez, Mateos Mateos y Martínez Arias) — no CUMANIN-2 —, pág. 83.
Transcrita a mano desde foto del equipo (2026-09-10); **pendiente de verificar línea
a línea contra el libro físico** antes de usarla en evaluaciones reales. El archivo
ya está gitignored (`config/baremos.csv` nunca se sube al repo).

```
tramo_edad , pd , T , percentil
36_42      , 0  , 48.7, 45
...
```

- `tramo_edad`: **6 tramos reales de la Tabla B.9, en meses** (no son de ancho
  uniforme): `36_42`, `43_48`, `49_54`, `55_60`, `61_66`, `67_78`. El estudio
  (3;0-5;11 = 36-71 meses) usa los primeros 5 completos y parte del último
  (67-71 de los 67-78 que llegan hasta 6;6).
- `pd`: puntuación directa (nº de figuras acertadas, 0-15).
- `percentil`: **publicado directamente en la Tabla B.9** — es el dato real.
- `T`: **la Tabla B.9 NO publica T para esta subescala.** La columna `T` de este CSV
  es una estimación matemática a partir del percentil (`T = 50 + 10·Φ⁻¹(Pc/100)`,
  asumiendo distribución normal), calculada en `scripts` de generación, no un valor
  del manual. Los cortes "T ≤ 40 en riesgo / T ≤ 30 derivar" que usa
  `scoring/niveles.py` (citando pág. 98-99) **no están verificados contra esta
  edición del manual ni contra esta subescala** — el equipo no tiene todavía esas
  páginas fotografiadas. Tratar como pendiente de validar con el asesor (ver
  ESTADO.md), igual que el resto de la categorización de nivel global.

Filas faltantes de `pd` se interpolan linealmente (aunque la Tabla B.9 ya cubre
los 16 valores de `pd`, 0 a 15, para cada tramo).

## Anonimización y ética

- `child_id` es un código; ningún dato personal en las carpetas ni en los CSV.
- Consentimiento de padres/apoderados y aval del Comité de Ética gestionados fuera de este
  repositorio (se eliminó el asentimiento de los niños).
- Son datos de menores: **nunca subir `data/raw/`** a un repositorio público.
- Registrar **versión de baremo** y **hash de git del modelo** en cada informe
  (van en `panel_tecnico` y en `models/actual/manifiesto.json`).
