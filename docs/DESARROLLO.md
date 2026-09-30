# Guía de desarrollo

Convenciones del código para que cualquier miembro del equipo pueda leerlo, cambiarlo y
reproducir los resultados del artículo.

## Entorno

```bash
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -e ".[dev]"
pip install -r requirements-dl.txt                   # modelo B (PyTorch + CUDA)
pre-commit install
```

- `pyproject.toml` es la fuente de verdad de las dependencias; `requirements.txt` se
  mantiene solo por compatibilidad.
- Antes de subir cambios: `ruff check src scripts tests` y `pytest -q` (pre-commit corre
  ruff solo).

## Organización

| Capa | Dónde | Regla |
|---|---|---|
| Lógica reutilizable | `src/grafomotor/<paquete>/` | funciones puras y testeables; sin `print`, sin rutas fijas |
| Orquestación | `src/grafomotor/comandos/` | un módulo por paso: lee artefactos, llama a la lógica, escribe resultados |
| Entrada | `grafomotor <comando>` (`cli.py`) | los scripts de `scripts/` son envoltorios de 3 líneas |
| Nombres de archivos | `artefactos.py` | ningún otro módulo arma a mano "oof_dl_<x>.parquet" |
| Configuración | `config/config.yaml` | los hiperparámetros y rutas no van en el código |

Dependencias entre capas: `comandos` → paquetes de lógica → `io`/`config`/`logs`. Un
módulo de lógica nunca importa de `comandos`. `evaluation/` no importa PyTorch, para que
el modelo A funcione sin las dependencias de DL.

## Añadir un comando

1. Crear `src/grafomotor/comandos/mi_paso.py` con:

   ```python
   AYUDA = "qué hace, en una línea"

   def agregar_argumentos(p: argparse.ArgumentParser) -> None: ...

   def ejecutar(args: argparse.Namespace, cfg: Config) -> int:   # 0 = éxito
       ...
   ```

2. Registrarlo en `COMANDOS` de `src/grafomotor/cli.py`.
3. Si produce archivos nuevos, añadir su nombre en `artefactos.py`.
4. (Opcional) un envoltorio en `scripts/NN_mi_paso.py` si forma parte de la cadena numerada.

`tests/test_infraestructura.py` comprueba que cada comando registrado cumple la interfaz.

## Estilo

- Nombres en español, como el dominio (figura, niño, puntaje, baremo). Los paquetes
  heredados (`preprocessing`, `features`, `model`, `evaluation`) mantienen su nombre para no
  romper importaciones.
- Mensajes con `log = obtener_logger(__name__)`; `print` solo para el resultado final que el
  usuario pidió (tablas, JSON).
- Tipado en las firmas públicas y docstring que diga QUÉ hace y POR QUÉ (el cómo lo dice el
  código).
- `zip(..., strict=True)` cuando las secuencias deben tener el mismo largo.
- Nada de datos personales en el código ni en los logs: solo `child_id`.

## Reproducibilidad

- Particiones por niño fijas y compartidas por A y B: `data/processed/particiones.csv`
  (semilla en `evaluation/particiones.py`). Si cambian los niños, se regeneran solas.
- Semillas: `dl.semilla` en `config.yaml`; `--semillas N` reporta la variabilidad.
- Cada modelo A guarda un manifiesto con hash de git, fecha, hiperparámetros y versión de
  baremo (`models/actual/manifiesto.json`); cada variante de B guarda su configuración en
  `models/dl/<variante>/historial.json`.
- La caché de robustez de A se invalida sola si cambian las particiones, el modelo A, los
  indicadores o el preprocesamiento. Si se modifica una degradación, subir
  `VERSION` en `evaluation/degradaciones.py`.

## Buenas prácticas de evaluación (no negociables para el artículo)

- Nunca afinar hiperparámetros mirando el fold de prueba: solo con la validación interna.
  El modelo A ya usa validación anidada (`modelo.cv.anidada: true`); para B, decidir TTA,
  resolución, aumento y arquitectura con la validación interna o fijarlos de antemano.
- No afinar con datos sintéticos: sirven para probar el código, no para decidir.
- Reportar variabilidad entre semillas del modelo B y p-valores corregidos por Holm.
- Las etiquetas son del evaluador experto; la docente no califica.

## Tests

| Archivo | Cubre |
|---|---|
| `test_scoring.py` | tramos de la Tabla B.9, cortes de nivel |
| `test_features.py` | indicadores geométricos |
| `test_plain_language.py` | informe para el docente (sin jerga, frases cortas) |
| `test_contract_inferencia.py` | el modelo servido da la salida validada |
| `test_comparacion.py` | métricas, CCI, PD con regla de 4 fallos, McNemar, bootstrap, degradaciones |
| `test_dl.py` | red multicabeza, fases, aumentos sin volteos, Grad-CAM (se salta sin PyTorch) |
| `test_identificacion.py` | P(riesgo) Poisson-binomial, Wilson, triaje, evaluación selectiva, calibración, balance por figura, validación por colegio |
| `test_infraestructura.py` | CLI, nombres de artefactos, JSON, Holm, validación anidada, errores, acuerdo entre evaluadores |
