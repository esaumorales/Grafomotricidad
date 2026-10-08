# Estado del proyecto y qué es real vs. marcador de posición

## Diseño comparativo ML vs DL (decisión del 30/09/2026) — implementado

Se comparan dos enfoques con los mismos datos (reemplaza el "se descartaron las CNN" del
documento de contexto):

- **Modelo A** (se mantiene): visión clásica + 6 indicadores + XGBoost + SHAP.
- **Modelo B** (nuevo, `src/grafomotor/dl/`): preprocesamiento mínimo (perspectiva + recorte
  224×224) + **ResNet-18** preentrenada con red común y 15 cabezas (EfficientNet-B0 como
  alternativa, `--arq efficientnet_b0`), entrenamiento en dos fases con pesos por clase y
  figura, aumento moderado sin volteos (un test lo exige) y **Grad-CAM**.
- **Evaluación común** (`src/grafomotor/evaluation/`): particiones por niño compartidas
  (`particiones.csv`), kappa de Cohen **sin ponderar** por figura (antes se usaba QWK),
  CCI + Bland-Altman de la PD, kappa ponderado del nivel, todo por edad (3/4/5 años),
  McNemar por figura y bootstrap por niño de Δkappa y ΔCCI, robustez (degradaciones
  sintéticas + doble foto si existe), practicidad y chequeo de atajos con Grad-CAM.
- **Dos PD** (`scoring/pd.py`): completa y del manual (regla de 4 fallos seguidos a posteriori).
- Probado de punta a punta con datos sintéticos en la GPU local (RTX 4070 SUPER):
  `python run_all.py --sinteticos --dl`. Las cifras con datos sintéticos **no dicen nada**
  sobre el rendimiento real; solo prueban que la cadena funciona.

Variantes del modelo B (30/09/2026): perfil de aumento `robusto` (sombra, desenfoque y luz
más intensos + desplazamiento y escala leves; sin volteos) y repetición con varias semillas
(`--semillas 3`, media ± DE). `13_resumen_variantes.py` las tabula frente a A. Aviso para el
artículo: la robustez sintética usa las mismas familias de degradación que el aumento
`robusto`, así que esa variante parte con ventaja en esa prueba; la evidencia limpia es la
doble foto. Los hiperparámetros NO se afinan con datos sintéticos: se hace con los reales y
solo con la validación interna (nunca mirando el fold de prueba).

Buenas prácticas aplicadas tras revisar la literatura (30/09/2026): validación anidada del
modelo A (la fuga anterior inflaba el kappa del nivel en ~5 puntos), ensamble de semillas y
TTA sin reentrenar (`ensamblar-dl`), resolución configurable (`--lado`), galería de errores
(`errores`), prueba de aleatorización de Grad-CAM (Adebayo et al., 2018) y acuerdo entre
evaluadores (`acuerdo-evaluadores`, CLAIM 2024). Hallazgo: el TTA mejora ResNet-18 pero
empeora EfficientNet-B0, por eso queda desactivado por defecto y se decide con la
validación interna. Con datos sintéticos, la doble calificación está SIMULADA
(`data/labels/doble_calificacion.csv`); con datos reales hay que sustituirla.

Evaluación e identificación (30/09/2026): calibración cruzada de Platt; identificación por
niño con P(riesgo) exacta (distribución de la PD), triaje con zona gris a revisión humana y
sensibilidad/VPN con IC de Wilson (`identificar`); evaluación selectiva por figura; informe
de balance por figura en `validar` (clase minoritaria por figura frente a mínimos
orientativos); curva de aprendizaje (`curva-aprendizaje`); validación externa por colegio
(`comparacion.agrupar_por: colegio`, columna `colegio` en etiquetas.csv). Con ~300 niños de
varios colegios, correr `validar` y la curva de aprendizaje para confirmar que alcanzan.

Niveles del niño (30/09/2026): criterio único y configurable (`scoring.niveles` en
config.yaml: base percentil o T, cortes, acción y fuente). Hoy PROVISIONAL (base T, cortes
40/30, mismos resultados que antes); pendiente sustituirlo por los cortes oficiales en
percentil que aporte el equipo, con su fuente.

Pendiente en este frente:
- **Doble foto por hoja (URGENTE, antes del 12/10):** decidir si se toma. Sin ella la
  robustez solo se mide con degradaciones sintéticas. El código ya la soporta
  (`data/labels/fotos_aula.csv`, ver `docs/DATOS.md`).
- **Regla de 4 fallos:** decidir con el asesor qué PD es la oficial (se reportan ambas).
- Cuello de botella de conceptos (Koh et al., 2020): solo si el asesor lo pide; no implementado.
- La app web sigue usando solo el modelo A (es un agregado; el foco son los modelos).

## Datos reales (2026-10-08)

46 niños (NIN-01..46) fotografiados/escaneados: hojas -> `scripts/14_segmentar_hojas.py` ->
`data/raw_reales/<niño>/F01..F15.jpg` (690 figuras). `scripts/15_preparar_reales.py` genera,
sin necesitar calificaciones, `data/real/interim` (modelo A), `data/real/interim_dl` (modelo B,
224x224) y `data/real/processed/features.parquet`. Se usa `config/config_real.yaml` (rutas
reales; si cambias parámetros en config.yaml, cópialos allí). Con las calificaciones llenas en
`data/hojas_reales/calificacion_46_ninos.xlsx`, `scripts/16_cargar_calificaciones.py` produce
`data/real/labels/etiquetas.csv` y se entrena con `grafomotor --config config/config_real.yaml ...`.
Pendiente: repetir fotos de NIN-06 (hoja 1), NIN-10 (hoja 2) y NIN-11 (hojas 2 y 3).

## Listo y probado de punta a punta

- Estructura completa del paquete `grafomotor` + scripts 00–06 + `run_all.py`.
- Cadena completa ejecutable: `python run_all.py --sinteticos`
  (genera plantillas y datos falsos, preprocesa, extrae features, entrena, evalúa).
- App web (FastAPI) funcionando: `python scripts/06_servir_web.py`.
- Capa de explicación para el docente **implementada y testeada**
  (`tests/test_plain_language.py`: sin jerga, frases cortas, panel técnico separado).
- Tests: `pytest -q`.

## Actualizado con las 15 figuras reales del Anexo 2 (2026-09-13)

`config.yaml > figuras` y `data/templates/F01.png` … `F15.png` ya tienen las 15 figuras de
la escala de Visopercepción (el documento de contexto las llamaba "Anexo 2"; son las mismas
del CUMANIN original y del CUMANIN-2), en el orden y con los nombres reales del manual — antes solo había 6 figuras de relleno en un orden arbitrario. `scripts/gen_plantillas.py`
las dibuja como **vectores fieles a la forma/topología** descrita en el criterio de corrección
(sección 2.2 del contexto del proyecto), no como escaneo del manual (no se versiona por derechos
de autor). Si el equipo consigue la digitalización oficial, se puede sustituir cada PNG 1:1
(mismo nombre de archivo) sin tocar el resto del pipeline.

`vertices_esperados` / `intersecciones_esperadas` en `config.yaml` se calcularon corriendo el
mismo algoritmo de `features/indicadores.py` sobre cada plantilla contra sí misma (no a ojo),
para que una copia perfecta dé error 0. Al hacerlo se detectó que `_puntos_cruce` (usado por el
indicador "intersecciones") cuenta puntos de ramificación del esqueleto, no cruces geométricos
reales: en figuras con varias líneas gruesas que se tocan (F03, F06, F07, F09, F11, F12, F15)
esto infla el conteo con artefactos de grosor de trazo — el caso más claro es F09 (rectángulo +
X), que da 18 en vez de 1 cruce real. El indicador queda autoconsistente pero es sensible al
temblor de trazo en esas figuras; **revisar `_puntos_cruce` antes de confiar en "intersecciones"
para cualquier figura con más de un cruce real**, es parte de la calibración pendiente de abajo.

## Corrección de instrumento: CUMANIN original, no CUMANIN-2 (2026-09-10/13)

El equipo aclaró que la corrección se basa en el **CUMANIN original** (Portellano
Pérez, Mateos Mateos y Martínez Arias), no en CUMANIN-2 — el alcance sigue siendo
solo la escala de Visopercepción. Con fotos del equipo del Apéndice C (criterios
letra por letra de las 15 figuras) y la Tabla B.9 (pág. 83) se corrigió:

- `config/baremos.csv`: ahora es la Tabla B.9 real (PD → **percentil**, no T — esa
  tabla no publica T para esta subescala). 6 tramos de edad reales en meses
  (`36_42`…`67_78`), no los 9 tramos de 4 meses que se habían asumido. La columna
  `T` del CSV es una estimación matemática desde el percentil, no un dato oficial.
- **Sin verificar todavía:** los cortes `T ≤ 40` / `T ≤ 30` y la Tabla 5.2 de
  `scoring/niveles.py` citan "manual, pág. 98-99", pero el equipo no ha fotografiado
  esas páginas ni confirmado que correspondan a esta edición/subescala. No se han
  tocado en código; siguen siendo la misma categorización pendiente de validar con
  el asesor que ya señalaba el PPI, ahora con una razón adicional para revisarla.

## MARCADOR DE POSICIÓN — sustituir cuando tengas los datos

| Qué | Archivo(s) | Cómo sustituir |
|---|---|---|
| Figuras de referencia | `data/templates/F01.png` … `F15.png` | ✅ ya son las 15 reales (ver arriba); solo sustituir por escaneo oficial si el equipo lo consigue |
| Baremo PD → Pc | `config/baremos.csv` | ✅ transcrito de la Tabla B.9 real (CUMANIN original, pág. 83) — **pendiente de verificar línea a línea contra el libro físico** antes de usarlo en evaluaciones reales (ver docs/DATOS.md) |
| Fotos de los niños | `data/raw/<child_id>/<figura_id>.jpg` | tus fotos reales |
| Etiquetas | `data/labels/etiquetas.csv` | corrección 0/1 del evaluador experto (el equipo), las 15 figuras (ver `docs/DATOS.md`) |
| Doble foto | `data/labels/fotos_aula.csv` | opcional: foto de aula de la misma hoja |
| Config de figuras | `config.yaml > figuras` | ✅ ya tiene F01…F15 reales; solo recalibrar `vertices_esperados`/`intersecciones_esperadas` si se sustituyen las plantillas por el escaneo oficial |
| Nº de clases del nivel | `config.yaml > scoring > n_clases` | 2 (por defecto) o 3 según la distribución real |
| Test de contrato | `tests/test_contract_inferencia.py` → `CASOS_FIJOS` | rellenar con vectores reales tras entrenar |

## Pasos para pasar a datos reales

```bash
# 1. limpiar lo sintético
rm -rf data/raw/* data/interim/* data/interim_dl/* data/processed/* data/templates/*
rm -rf data/labels/etiquetas.csv models/actual/* models/dl/*

# 2. colocar tus datos (ver tabla de arriba)

# 3. correr la cadena con TUS datos
python run_all.py --dl       # sin --sinteticos

# 4. revisar data/processed/evaluacion_ml.json y, con --dl, comparacion_resnet18.md
# 5. demo del informe:  python scripts/05_explicar_demo.py --child-id <uno_de_los_tuyos>
```

## Pendiente de calibración con material real

- Umbrales de `preprocessing/pipeline.py` (binarizado, detección de la hoja, ECC).
- Tolerancias de `features/indicadores.py` (px de cierre, °/45 de ángulo, escala de proporción).
- `_puntos_cruce` en `features/indicadores.py`: cuenta ramificaciones del esqueleto como si fueran
  cruces reales; da cifras infladas en figuras con >1 línea gruesa que se toca (ver nota arriba).
- `explain/phrases.py`: revisar el fraseo con un docente real (comprensibilidad).
- `explain/suggestions.py`: validar las actividades con la práctica de aula.
