# Estado del proyecto y qué es real vs. marcador de posición

## Listo y probado de punta a punta

- Estructura completa del paquete `grafomotor` + scripts 00–06 + `run_all.py`.
- Cadena completa ejecutable: `python run_all.py --sinteticos`
  (genera plantillas y datos falsos, preprocesa, extrae features, entrena, evalúa).
- App web (FastAPI) funcionando: `python scripts/06_servir_web.py`.
- Capa de explicación para el docente **implementada y testeada**
  (`tests/test_plain_language.py`: sin jerga, frases cortas, panel técnico separado).
- Tests: `pytest -q`.

## Actualizado con las 15 figuras reales del Anexo 2 (2026-09-13)

`config.yaml > figuras` y `data/templates/F01.png` … `F15.png` ya tienen las 15 figuras del
Anexo 2 del CUMANIN-2 (Prueba 6, Visopercepción), en el orden y con los nombres reales del
manual — antes solo había 6 figuras de relleno en un orden arbitrario. `scripts/gen_plantillas.py`
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

## MARCADOR DE POSICIÓN — sustituir cuando tengas los datos

| Qué | Archivo(s) | Cómo sustituir |
|---|---|---|
| Figuras de referencia | `data/templates/F01.png` … `F15.png` | ✅ ya son las 15 reales (ver arriba); solo sustituir por escaneo oficial si el equipo lo consigue |
| Baremo PD → T | `config/baremos.csv` | descargar la tabla oficial por tramo de edad de teacorrige.com; anotar versión |
| Fotos de los niños | `data/raw/<child_id>/<figura_id>.jpg` | tus fotos reales |
| Etiquetas | `data/labels/etiquetas.csv` | corrección 0/1 del docente evaluador (ver `docs/DATOS.md`) |
| Config de figuras | `config.yaml > figuras` | ids, nombres, `vertices_esperados`, `intersecciones_esperadas` reales; añadir F07…F15 |
| Nº de clases del nivel | `config.yaml > scoring > n_clases` | 2 (por defecto) o 3 según la distribución real |
| Test de contrato | `tests/test_contract_inferencia.py` → `CASOS_FIJOS` | rellenar con vectores reales tras entrenar |

## Pasos para pasar a datos reales

```bash
# 1. limpiar lo sintético
rm -rf data/raw/* data/interim/* data/processed/* data/templates/*
rm -f data/labels/etiquetas.csv models/actual/*

# 2. colocar tus datos (ver tabla de arriba)

# 3. correr la cadena con TUS datos
python run_all.py            # sin --sinteticos

# 4. revisar data/processed/evaluacion.json  (F1 por figura, QWK, Bland-Altman, por tramo)
# 5. demo del informe:  python scripts/05_explicar_demo.py --child-id <uno_de_los_tuyos>
```

## Pendiente de calibración con material real

- Umbrales de `preprocessing/pipeline.py` (binarizado, detección de la hoja, ECC).
- Tolerancias de `features/indicadores.py` (px de cierre, °/45 de ángulo, escala de proporción).
- `_puntos_cruce` en `features/indicadores.py`: cuenta ramificaciones del esqueleto como si fueran
  cruces reales; da cifras infladas en figuras con >1 línea gruesa que se toca (ver nota arriba).
- `explain/phrases.py`: revisar el fraseo con un docente real (comprensibilidad).
- `explain/suggestions.py`: validar las actividades con la práctica de aula.
