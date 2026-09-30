# Evaluación grafomotora infantil: aprendizaje automático vs. aprendizaje profundo explicables

Calificación automática, figura por figura, de la escala de **Visopercepción del CUMANIN
original** (Portellano Pérez et al., 2002; 15 figuras, cada una 0/1) a partir de la
**foto** de la hoja de niños peruanos de **3 a 5 años**. Se **comparan dos enfoques** con
los mismos datos:

| | Modelo A — ML clásico | Modelo B — DL |
|---|---|---|
| Entrada | foto → pipeline de visión clásica (perspectiva, iluminación, binarizado, aislar trazo, registro a plantilla) | foto → preprocesamiento **mínimo** (perspectiva + recorte 224×224) |
| Modelo | **6 indicadores geométricos** + **XGBoost** | **ResNet-18** preentrenada (EfficientNet-B0 como alternativa), red común + 15 cabezas |
| Explicación | **SHAP**: *qué* criterio falló | **Grad-CAM**: *dónde* miró la red |
| Código | `preprocessing/`, `features/`, `model/`, `explain/` | `dl/` |

Las dos rutas se evalúan con las **mismas particiones por niño**, las mismas etiquetas del
evaluador experto y las mismas métricas (`evaluation/`). La app web (FastAPI + React) es
un agregado: usa el modelo A y entrega al docente un informe en lenguaje natural.

Documentación: [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md) ·
[`docs/EXPLICABILIDAD.md`](docs/EXPLICABILIDAD.md) · [`docs/DATOS.md`](docs/DATOS.md) ·
[`ESTADO.md`](ESTADO.md)

---

## Los 6 indicadores del modelo A (Tabla 1 del PPI)

| clave | nombre para el docente | criterio del CUMANIN |
|---|---|---|
| `precision_modelo` | Parecido general con el modelo | similitud global |
| `vertices` | Esquinas de la figura | número de ángulos |
| `error_angular` | Inclinación de los ángulos | tolerancia angular (≤ 45°) |
| `cierre` | Cierre de las figuras | cierre de la figura |
| `intersecciones` | Cruce de líneas | respeto de intersecciones |
| `proporcion` | Tamaño de las partes | proporción |

## Comparación justa (reglas comunes)

- **Particiones:** `StratifiedGroupKFold` por niño → `data/processed/particiones.csv`,
  leído por los dos modelos. Todas las figuras de un niño van al mismo fold.
- **Por figura (0/1):** exactitud balanceada, F1 macro, sensibilidad, especificidad y
  **kappa de Cohen sin ponderar**.
- **PD total:** CCI de acuerdo absoluto y Bland-Altman. Se reportan **dos PD**: la completa
  (15 figuras) y la del manual (regla de parar tras 4 fallos seguidos, aplicada a posteriori).
- **Nivel de desempeño:** kappa ponderado.
- Todo también **por edad** (3, 4 y 5 años).
- **Entre modelos:** McNemar exacto por figura y bootstrap por niño (IC 95 % de la diferencia
  de kappa y de CCI).
- **Robustez:** fotos de aula (doble foto, si existe `data/labels/fotos_aula.csv`) y
  degradaciones sintéticas (sombra, desenfoque, inclinación, brillo).
- **Practicidad:** nº de pasos, segundos por hoja y tasa de fallos.
- **Explicabilidad:** SHAP (qué criterio) vs. Grad-CAM (qué región); Grad-CAM se usa además
  para verificar que la red mire el trazo y no sombras o bordes.

## Nivel de desempeño

PD → percentil por tramo de edad en meses (**Tabla B.9**, pág. 83) → T estimada desde el
percentil → nivel. Cortes: **T ≥ 41** Adecuado · **31–40** En riesgo · **≤ 30** Derivar
(`corte_bajo_T: 40`, `corte_muy_bajo_T: 30`; **pendientes de validar con el asesor**).
2 clases por defecto (Adecuado / En riesgo).

## Puesta en marcha

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
pip install -e ".[dev]"                 # paquete + herramientas (pytest, ruff, pre-commit)
pip install -r requirements-dl.txt      # modelo B: PyTorch con CUDA (ver el archivo para CPU)
pre-commit install                      # ruff y chequeos antes de cada commit
```

Todo se ejecuta con un único comando, `grafomotor` (o `python -m grafomotor`):

```bash
grafomotor --help                        # lista de comandos en orden de la cadena
grafomotor <comando> --help              # opciones de un comando
```

Los scripts numerados de `scripts/` siguen funcionando: son envoltorios de 3 líneas de
estos mismos comandos (`python scripts/08_dl_entrenar.py --arq ...` = `grafomotor entrenar-dl --arq ...`).

### Con datos sintéticos (probar la cadena)

```bash
grafomotor todo --sinteticos            # plantillas + 150 niños falsos + modelo A
grafomotor todo --sinteticos --dl       # ... + modelo B + comparación + robustez + Grad-CAM
```

### Con datos reales, paso a paso

| Paso | Comando | Qué hace |
|---|---|---|
| 00 | `grafomotor validar` | esquema de etiquetas, edades, desbalance |
| 01 | `grafomotor preprocesar` | A: binarizado + registro a plantilla → `data/interim/` |
| 02 | `grafomotor extraer-features` | A: 6 indicadores → `features.parquet` |
| 03 | `grafomotor entrenar-ml` | A: XGBoost, Grid Search con CV agrupada por niño |
| 04 | `grafomotor evaluar-ml` | A: out-of-fold **anidado** con particiones compartidas → `oof_ml.parquet` |
| 07 | `grafomotor preparar-dl` | B: perspectiva + recorte 224×224 → `data/interim_dl/` |
| 08 | `grafomotor entrenar-dl --final` | B: 2 fases por fold → `oof_dl_<variante>.parquet` |
| 09 | `grafomotor comparar --arq <variante>` | A vs B: métricas, McNemar + Holm, bootstrap |
| 10 | `grafomotor robustez --arq <variante>` | degradaciones sintéticas + doble foto |
| 11 | `grafomotor gradcam --arq <variante>` | dónde mira la red y si usa atajos |
| 12 | `grafomotor practicidad --arq <variante>` | pasos, segundos por hoja, fallos |
| 13 | `grafomotor resumen-variantes` | todas las variantes de B frente a A (y el techo humano) |
| 14 | `grafomotor ensamblar-dl --base <variante>` | B: ensamble de semillas + TTA sin reentrenar |
| 15 | `grafomotor errores [--arq <variante>]` | galería de figuras mal calificadas, para revisar a mano |
| 16 | `grafomotor acuerdo-evaluadores` | acuerdo entre dos evaluadores expertos (techo humano) |
| 05 | `grafomotor explicar --child-id NINO_0007` | informe para el docente |
| 06 | `grafomotor servir` | app web en http://127.0.0.1:8000 |

Variantes del modelo B (`entrenar-dl`): `--arq efficientnet_b0` (arquitectura alternativa),
`--aumento robusto` (más sombra, desenfoque y luz → variante `<arq>_robusto`),
`--lado 320` (más resolución; antes `preparar-dl --lado 320`) y `--semillas 3` (media ± DE
entre semillas). El nombre de la variante es el que se pasa
como `--arq` a los pasos 09-12.

Resultados en `data/processed/` (nombres definidos en `src/grafomotor/artefactos.py`).

## Buenas prácticas aplicadas

| Práctica | Referencia | Dónde |
|---|---|---|
| División por niño (sin fuga entre figuras de un mismo niño) | estudios de fuga por sujeto en imagen médica | `evaluation/particiones.py` |
| Validación cruzada anidada: hiperparámetros elegidos sin ver el fold de prueba | Varma y Simon (2006) | `model/train.py::ajustar_anidado` |
| Pocas capas ajustadas, aumento + dropout + parada temprana | guías de transfer learning con datos pequeños | `dl/entrenar.py` |
| Red común + una cabeza por elemento, aumento y TTA | Langer et al. (2024) | `dl/modelo.py`, `ensamblar-dl` |
| Varias semillas (media ± DE) y ensamble | práctica estándar en DL | `entrenar-dl --semillas`, `ensamblar-dl` |
| McNemar con corrección de Holm, bootstrap por niño | comparación de clasificadores | `evaluation/comparacion.py` |
| Revisión manual de errores | imagen médica con pocos datos | `grafomotor errores` |
| Prueba de aleatorización de Grad-CAM | Adebayo et al. (2018) | `grafomotor gradcam` |
| Acuerdo entre evaluadores del estándar de referencia | CLAIM 2024 | `grafomotor acuerdo-evaluadores` |
| Guías de reporte para el artículo | TRIPOD+AI (2024), CLAIM (2024) | — |

Regla: **TTA, resolución, aumento y arquitectura se eligen con la validación interna**, nunca
comparando cifras del fold de prueba (eso infla los resultados).

## Estructura del código

```
src/grafomotor/
├── cli.py              punto de entrada `grafomotor <comando>`
├── comandos/           un módulo por paso: solo orquesta (lee, llama a la lógica, escribe)
├── config.py           carga de config/config.yaml
├── artefactos.py       nombres y rutas de todos los archivos que produce la cadena
├── io.py               etiquetas, imágenes, plantillas, JSON
├── logs.py             logging común
├── predictores.py      A y B con la misma interfaz: foto → probabilidad (robustez, practicidad)
├── datos/              plantillas vectoriales y dataset sintético
├── preprocessing/      A: visión clásica (perspectiva, iluminación, binarizado, registro)
├── features/           A: los 6 indicadores geométricos
├── augment/            A: aumento seguro para la etiqueta
├── model/              A: XGBoost (dataset, entrenamiento, CV por fold, registro)
├── dl/                 B: imagen mínima, aumentos, red multicabeza, entrenamiento, Grad-CAM
├── evaluation/         común: métricas, particiones, reporte, comparación, degradaciones
├── scoring/            PD (completa y regla de 4 fallos), baremo Tabla B.9, niveles
├── explain/            SHAP → informe en lenguaje natural para el docente
└── webapp/             API FastAPI + SQLite (la app React está en frontend/)
```

Convenciones para el equipo (añadir un comando, tests, estilo): [`docs/DESARROLLO.md`](docs/DESARROLLO.md).

## Aviso

Herramienta de **apoyo pedagógico**, no de diagnóstico clínico. La prueba la aplica
siempre una persona; el sistema solo califica. Las figuras, criterios y baremos del
CUMANIN son material propietario (TEA Ediciones): no se versionan (`config/baremos.csv`
y `data/` están en `.gitignore`). Son datos de menores: **nunca subir `data/raw/`** a un
repositorio público. Los baremos son de España y llegan hasta los 6;11 años: declararlo
como limitación.
