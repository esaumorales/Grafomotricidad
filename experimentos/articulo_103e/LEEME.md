# Experimento del artículo (103 niños, 1,545 figuras)

Scripts que producen los resultados del artículo para Frontiers in Education: la comparación de los seis
modelos (3 de ML y 3 de DL), la ablación, la prueba con 20 niños apartados, la revisión por confianza, el
análisis con las etiquetas por mayoría y las figuras de resultados. Usan el código del proyecto (`src/grafomotor`).

**Los datos no están en el repositorio.** Las fotografías, las calificaciones y los archivos derivados
(`etiquetas.csv`, `participantes_103.csv`, `processed/*.parquet`, `mejora/apartados.csv`, etc.) son de menores de
edad y el consentimiento de los padres no permite su difusión. Las rutas a esos datos están en `config.yaml`
(sección `rutas`) y al inicio de `paso1_datos.py`, `mejora/paso10_etiquetas_mayoria.py` y `mejora/paso11_mayoria.py`;
hay que ajustarlas a la ubicación local de los datos.

## Orden de ejecución

| Paso | Script | Qué hace |
|---|---|---|
| 0 | `paso1_datos.py` | Recorta cada figura de la hoja enderezada con el recuadro revisado por el equipo y arma `etiquetas.csv` y `participantes_103.csv`. |
| 1 | `correr.sh` | `grafomotor preparar-reales` (procesamiento de imágenes de las dos ramas) y `exp_criterios.py` (los 3 modelos de ML con y sin los indicadores por criterio del manual: ablación). |
| 2 | `correr_dl.sh` | Entrena ResNet-18, MobileNetV2 y EfficientNet-B0 con las mismas particiones por niño, y `dl_corte.py` ajusta su punto de corte con los niños de validación interna. |
| 3 | `mejora/paso0_apartar.py` | Aparta 20 niños (estratificados por tercil de la PD, semilla fija) antes de ajustar el modelo final. |
| 4 | `correr_mejora.sh` | Modelo final con los 83 niños de desarrollo, prueba única con los 20 apartados (`paso4_prueba.py`), límites de la revisión por confianza (`paso5_confianza_V0.py`) y resumen de métricas sin kappa (`resumen_sin_kappa.py` → `resultados_sin_kappa.json`). |
| 5 | `mejora/paso10_etiquetas_mayoria.py` y `mejora/paso11_mayoria.py` | Etiquetas por mayoría de la revisión a ciegas y análisis de sensibilidad. |
| 6 | `figuras_resultados_103e.py <carpeta>` | Figuras 5 a 8 del artículo (PNG, TIF a 400 ppp y PDF) y los datos de cada una en CSV. |

Los scripts `.sh` usan el Python de la variable `PY` (por defecto `python`) y ponen `src/` en `PYTHONPATH`.

## Archivos

- `criterios.py`: indicadores por criterio del manual (número de partes, contacto, puntas libres, cruces,
  ondulaciones, esquinas, giro máximo e inclinación), medidos en el dibujo y en la figura modelo.
- `mejora/criterios2.py` y `mejora/paso2_criterios2.py`: indicadores adicionales probados durante el desarrollo
  (no forman parte del modelo final).
- `mejora/paso1_red.py`: probabilidad de EfficientNet-B0 como variable (variante híbrida probada en desarrollo).
- `mejora/paso3_evaluar.py`: variantes de Random Forest evaluadas solo con los 83 niños de desarrollo.

Semillas: 20260930 (particiones y modelos) y 20261024 (niños apartados y bootstrap de la prueba). Los intervalos
de confianza se estiman con 2,000 réplicas bootstrap por niño.
