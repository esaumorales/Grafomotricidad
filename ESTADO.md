# Estado del proyecto y qué es real vs. marcador de posición

## Listo y probado de punta a punta

- Estructura completa del paquete `grafomotor` + scripts 00–06 + `run_all.py`.
- Cadena completa ejecutable: `python run_all.py --sinteticos`
  (genera plantillas y datos falsos, preprocesa, extrae features, entrena, evalúa).
- App web (FastAPI) funcionando: `python scripts/06_servir_web.py`.
- Capa de explicación para el docente **implementada y testeada**
  (`tests/test_plain_language.py`: sin jerga, frases cortas, panel técnico separado).
- Tests: `pytest -q`.

## MARCADOR DE POSICIÓN — sustituir cuando tengas los datos

| Qué | Archivo(s) | Cómo sustituir |
|---|---|---|
| Figuras de referencia | `data/templates/F01.png` … | poner las figuras oficiales de la Visopercepción (Vis) del CUMANIN‑2, mismo nombre |
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
- `explain/phrases.py`: revisar el fraseo con un docente real (comprensibilidad).
- `explain/suggestions.py`: validar las actividades con la práctica de aula.
