# Sistema inteligente de evaluación grafomotora infantil (visión computacional + XGBoost)

Clasificación del nivel de desempeño grafomotor en **niños de 3 a 5 años** a partir de
**imágenes** de las figuras de la prueba **Visopercepción (Vis) del CUMANIN‑2**, con un
modelo de **gradient boosting (XGBoost)** y una capa de **explicación en lenguaje natural
para el docente**.

> Lo central de este proyecto **no** son las tablas ni los gráficos, sino que la IA
> **explique con palabras que un docente entienda** qué le cuesta al niño y qué hacer.
> Toda la parte numérica (puntuación T, percentiles, valores SHAP) vive en un *panel
> técnico* separado, pensado para el especialista.

---

## Flujo (resumen)

```
foto de la hoja
  → preprocesamiento (deskew, iluminación, binarizado, aislar figura, registrar a plantilla)
  → extracción de 6 indicadores geométricos por figura
  → XGBoost: puntúa cada figura (0/1) + probabilidad
  → scoring: suma → PD → baremo por tramo de edad → T → nivel (2 o 3 clases)
  → SHAP: qué indicadores explican el resultado
  → EXPLICACIÓN EN LENGUAJE NATURAL: informe para el docente + panel técnico
  → app web (FastAPI): el docente sube la foto y recibe el informe
```

Detalle de la arquitectura: [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md)
Diseño de la explicación para docentes: [`docs/EXPLICABILIDAD.md`](docs/EXPLICABILIDAD.md)
Esquema de datos y etiquetas: [`docs/DATOS.md`](docs/DATOS.md)

## Los 6 indicadores (Tabla 1 del PPI)

| clave | nombre para el docente | criterio CUMANIN‑2 |
|---|---|---|
| `precision_modelo` | Parecido general con el modelo | similitud global |
| `vertices` | Esquinas de la figura | número de ángulos |
| `error_angular` | Inclinación de los ángulos | tolerancia angular |
| `cierre` | Cierre de las figuras | cierre de la figura |
| `intersecciones` | Cruce de líneas | respeto de intersecciones |
| `proporcion` | Tamaño de las partes | proporción |

Rectitud del trazo y número de correcciones quedan como opcionales (`features/opcionales/`).

## Nivel de desempeño (target)

Se define con los **puntos de corte del CUMANIN‑2** sobre la T ajustada por edad
(manual, pág. 98‑99):

- **T ≥ 41** → Adecuado
- **T 31‑40** → Bajo (en riesgo — *screening*)
- **T ≤ 30** → Muy bajo (derivar)

El nº final de clases (**2**: Adecuado / En riesgo, o **3**) se fija según la
distribución observada en la muestra. Por defecto el proyecto arranca en **2 clases**.

## Puesta en marcha

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

### Opción A — ver todo funcionando ya (datos falsos)

```bash
python run_all.py --sinteticos      # plantillas + 150 niños de mentira + toda la cadena
python scripts/05_explicar_demo.py --child-id NINO_0007   # informe de un caso
python scripts/06_servir_web.py                            # http://localhost:8000
```

Genera datos SINTÉTICOS solo para probar el flujo. Ver `ESTADO.md` para pasar a datos reales.

### Opción B — con tus datos

```bash
# 1. valida el CSV de etiquetas y las carpetas
python scripts/00_validar_datos.py

# 2. preprocesa las fotos de data/raw/ -> data/interim/
python scripts/01_preprocesar.py

# 3. extrae features -> data/processed/features.parquet
python scripts/02_extraer_features.py

# 4. entrena (XGBoost por figura, CV agrupada por niño)
python scripts/03_entrenar.py

# 5. evalúa (F1 por figura, QWK, Bland-Altman, estratificado por tramo de edad)
python scripts/04_evaluar.py

# 6. demo del informe para docente sobre un caso
python scripts/05_explicar_demo.py --child-id NINO_0007

# 7. levanta la app web
python scripts/06_servir_web.py   # http://localhost:8000
```

O todo de una:  `python run_all.py`  (sin `--sinteticos`).

## Estado

Ver `ESTADO.md`. La cadena completa se ejecuta de punta a punta con `run_all.py --sinteticos`
(probado). Los módulos de visión (`preprocessing/`, `features/`) traen una
implementación base con OpenCV/scikit‑image que hay que calibrar con las figuras reales
del CUMANIN‑2. La capa de explicación (`explain/`) está implementada de forma completa
y determinista (plantillas), con un *hook* opcional de pulido por LLM desactivado.

## Aviso

Herramienta de **apoyo al docente**, no de diagnóstico. Las figuras y criterios del
CUMANIN‑2 son material propietario (TEA/Hogrefe); su uso aquí es estrictamente de
investigación. Registrar la **versión de baremo** utilizada (plataforma teacorrige.com).
