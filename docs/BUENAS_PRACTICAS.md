# Buenas prácticas del proyecto

Qué reglas sigue el código para mantenerse **ordenado, reproducible y fácil de leer**, y de
dónde salen. Está pensado para que cualquier persona nueva pueda aplicarlas.

## 1. Estructura del repositorio

```
Proyecto/
├── README.md              la portada: qué es y cómo empezar
├── ESTADO.md              qué es real y qué es provisional
├── pyproject.toml         dependencias y ajustes de las herramientas (un solo archivo)
├── config/                parámetros: rutas, cortes de nivel, umbrales (nada fijo en el código)
├── src/grafomotor/        el código, organizado por tema (ver abajo)
├── scripts/               envoltorios de 3 líneas de los comandos
├── tests/                 pruebas automáticas
├── docs/                  documentación (esta carpeta)
├── data/                  datos de los niños: NUNCA se suben (están en .gitignore)
└── models/                modelos entrenados: no se suben
```

Dentro de `src/grafomotor/` cada carpeta tiene **una sola responsabilidad**:

| Carpeta | Responsabilidad |
|---|---|
| `comandos/` | **Orquesta**: lee archivos, llama a la lógica, escribe resultados. Sin lógica propia |
| `preprocessing/` | Visión por computadora: enderezar, recortar, limpiar |
| `features/` | Los 6 indicadores geométricos |
| `model/` | Técnica A (XGBoost) |
| `dl/` | Técnica B (redes neuronales y Grad-CAM) |
| `evaluation/` | Métricas y comparación (comunes a A y B, para que sea justo) |
| `scoring/` | Puntaje, baremo y niveles |
| `explain/` | Explicaciones en lenguaje sencillo |
| `webapp/` | Aplicación web para la docente |

## 2. Las reglas que se aplican

| Regla | Por qué | Cómo se ve en el proyecto |
|---|---|---|
| **Un solo archivo de configuración** (`pyproject.toml`) | Todo el mundo instala igual y las herramientas leen los mismos ajustes | `pyproject.toml` |
| **Estructura `src/`** | Evita importar código sin querer desde la carpeta equivocada | `src/grafomotor/` |
| **Ruff** (revisión de estilo y errores) | Detecta errores y mantiene el estilo parejo, muy rápido | `ruff check src scripts tests` debe dar *All checks passed* |
| **Pruebas automáticas** (pytest) | Cada cambio se comprueba solo; si algo se rompe, se nota enseguida | `pytest -q` (todas deben pasar) |
| **Pre-commit** | Revisa el código **antes** de guardar cada cambio | `.pre-commit-config.yaml` |
| **Nada de números fijos escondidos** | Cambiar un parámetro no debe obligar a editar código | `config/config.yaml` |
| **Funciones pequeñas con nombre claro** | Se entiende lo que hacen sin leer el interior | `preprocessing/hoja.py` |
| **Documentar el "por qué"** | El código dice *qué* hace; el comentario explica *por qué* | Comentarios y docstrings en español |
| **Datos separados del código** | Los datos de menores no deben llegar a internet | `.gitignore`: `data/`, `models/` |
| **Datos reales y sintéticos separados** | No mezclar pruebas con datos de verdad | `config/config.yaml` vs `config/config_real.yaml` |
| **Reproducibilidad** | Los mismos pasos deben dar los mismos resultados | Semillas fijas, particiones guardadas en archivo |
| **Mensajes de commit claros** | El historial cuenta la historia del proyecto | `git log --oneline` |

## 3. Hábitos antes de subir cambios

```bash
ruff check src scripts tests      # ¿hay errores de estilo?
pytest -q                         # ¿siguen pasando las pruebas?
git status                        # ¿qué voy a subir? ¿hay datos de niños?
```

**Pregunta de seguridad antes de cada `git push`:** *¿hay fotos, nombres o datos de los niños
en lo que voy a subir?* Si la respuesta no es un "no" seguro, no se sube.

## 4. Cómo se documenta

Se sigue la idea de **separar los documentos según para qué sirven**:

| Tipo | Para quién | Dónde |
|---|---|---|
| **Portada** (qué es, cómo empezar) | Cualquiera | `README.md` |
| **Guía** (aprender cómo funciona) | Principiantes | `docs/GUIA_PRINCIPIANTE.md` |
| **Referencia** (datos exactos) | Quien programa | `docs/DATOS.md`, `docs/ARQUITECTURA.md` |
| **Decisiones** (qué se eligió y por qué) | El equipo | `ESTADO.md` |

Los diagramas se escriben con **Mermaid**: es texto dentro del propio `.md` y GitHub lo
dibuja solo. Ventaja: se pueden editar y quedan en el historial de cambios, igual que el código.

## 5. Fuentes consultadas

- Estructura de proyectos de machine learning y contenido de un buen README:
  [Structuring ML projects](https://apxml.com/courses/intermediate-python-programming-ml/chapter-6-efficient-maintainable-python-ml/structuring-ml-projects),
  [How to Document a Machine Learning Workflow](https://genxtechwriter.substack.com/p/how-to-document-a-machine-learning),
  [MLOps Coding Course: Readme](https://mlops-coding-course.fmind.dev/6.%20Sharing/6.2.%20Readme.html).
- Herramientas y organización de proyectos Python (`pyproject.toml`, estructura `src/`, Ruff,
  pytest, pre-commit): [Python project structure](https://tessl.io/registry/tessl-labs/python-project-structure/files),
  [Coding standards](https://fnb.readthedocs.io/latest/contributor-guide/coding-standards/).
- Diagramas en Markdown con Mermaid, soportados de forma nativa por GitHub:
  [GitHub diagrams with Mermaid](https://ardalis.com/github-diagrams-with-mermaid/),
  [Enhance your READMEs with native Mermaid diagrams](https://codebase.substack.com/p/enhance-your-readmes-with-native).
