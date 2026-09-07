# Datos: carpetas, esquema de etiquetas y baremo

## Carpetas (todo bajo `data/`, ignoradas por git)

```
data/
├── raw/            fotos originales:  raw/<child_id>/<figura_id>.jpg
├── interim/        figuras binarias registradas: <child_id>__<figura_id>.png
├── processed/      features.parquet, evaluacion.json
├── templates/      plantilla de referencia por figura: <figura_id>.png (binaria)
└── labels/
    └── etiquetas.csv   (copiar de etiquetas_ejemplo.csv y rellenar)
```

## `labels/etiquetas.csv`

| columna | oblig. | descripción |
|---|---|---|
| `child_id` | sí | código anónimo del niño/a (p. ej. `NINO_0007`) |
| `edad_meses` | sí | edad en meses el día de la prueba. **36–71** (3;0–5;11) |
| `figura_id` | sí | id de la figura (`F01`…), coherente con `config.yaml > figuras` |
| `imagen_path` | sí | ruta de la foto relativa a `data/` (`raw/NINO_0007/F03.jpg`) |
| `puntaje` | sí | **0 / 1** — corrección del docente evaluador según criterios del CUMANIN‑2 |
| `sexo` | no | `F` / `M` (los baremos del CUMANIN‑2 no distinguen sexo) |
| `evaluador` | no | código del evaluador (para acuerdo inter‑evaluador) |
| `fecha` | no | ISO `AAAA‑MM‑DD` |
| `version_baremo` | no | versión exacta usada (teacorrige.com) |

Una fila por **(niño, figura)**. `00_validar_datos.py` comprueba rango de edad,
duplicados y valores de `puntaje`, y avisa de desbalance / efecto suelo.

## `config/baremos.csv` (PD → T)

Copiar de `config/baremos_ejemplo.csv` y **sustituir por la tabla oficial** de la
Visopercepción (Vis) del CUMANIN‑2, por tramo de edad. Columnas:

```
tramo_edad , pd , T , percentil
3;0_3;3    , 0  , 28, 1
...
```

- `tramo_edad`: tramos de **4 meses** (12 en total en el CUMANIN‑2; el estudio usa los
  9 de 3;0 a 5;11). Formato `AA;MM_AA;MM`.
- `pd`: puntuación directa (nº de figuras acertadas).
- `T`: puntuación típica (media 50, DT 10). Cortes de detección: **T ≤ 40** en riesgo,
  **T ≤ 30** derivar (manual, pág. 98‑99).
- `percentil`: opcional (para el panel técnico).

Filas faltantes de `pd` se interpolan linealmente.

## Anonimización y ética

- `child_id` es un código; ningún dato personal en las carpetas ni en los CSV.
- Consentimiento de padres/apoderados, asentimiento del niño y aval del Comité de Ética
  gestionados fuera de este repositorio.
- Registrar **versión de baremo** y **hash de git del modelo** en cada informe
  (van en `panel_tecnico` y en `models/actual/manifiesto.json`).
