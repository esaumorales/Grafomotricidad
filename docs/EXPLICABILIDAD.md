# Explicabilidad: cómo la IA explica el resultado en lenguaje de docente

> Esto es **lo central del proyecto**. No importan tanto las tablas ni los gráficos:
> importa que un **docente de educación inicial** lea el informe y entienda **qué le
> cuesta al niño y qué puede hacer mañana en el aula**, sin saber nada de estadística
> ni de IA.

---

## 1. Principios

1. **Sin jerga.** Nunca aparecen en el texto del docente: *SHAP, XGBoost, modelo,
   vector, puntuación T, percentil, IoU, baremo, dataset, gradiente…* (lista completa en
   `explain/plain_language.JERGA_PROHIBIDA`, y se comprueba en los tests).
2. **Frases cortas y concretas** (≈ 25 palabras máx.).
3. **Cada dificultad trae dos cosas**: *qué significa* y *cómo se ve en la hoja*
   (un ejemplo visual que el docente reconoce).
4. **Siempre hay una acción**: qué hacer en el aula, o a quién derivar.
5. **El resultado va primero**, en una frase, sin números.
6. **Separación estricta**: la narrativa para el docente y el *panel técnico*
   (T, percentil, tabla SHAP) son secciones distintas. El docente lee la narrativa;
   el especialista, si quiere, despliega el panel.
7. **Honestidad sobre la incertidumbre**: si las fotos salieron mal o el modelo dudó,
   el informe lo dice y pide revisar.
8. **Determinista**: el mismo caso produce siempre el mismo informe (plantillas, no un
   LLM). Reproducible y auditable para la tesis.

---

## 2. De los números al texto (pipeline de la explicación)

```
predicción por figura (0/1 + prob) + indicadores  ─┐
                                                    ├─► SHAP por figura
nivel (T → Adecuado / En riesgo / Derivar) ─────────┘        │
                                                             ▼
                                        agregación por sesión (media con signo
                                        de la contribución de cada indicador)
                                                             │
                    ┌────────────────────────────────────────┤
                    ▼                                         ▼
        fortalezas = indicadores con                dificultades = indicadores con
        contribución + y valor alto                 contribución − (empujaron a "falla")
                    │                                         │
                    │                        severidad = f(valor medio del indicador):
                    │                          ≥0.75 no es dificultad
                    │                          0.55–0.75  leve
                    │                          0.35–0.55  moderada
                    │                          <0.35      marcada
                    ▼                                         ▼
        frase de fortaleza                    frase (indicador × severidad):
        + "se ve en el círculo…"                "qué significa" + "cómo se ve en la hoja"
                                                + figura donde peor salió
                                                + 2 actividades de aula
                    └───────────────┬─────────────────────────┘
                                    ▼
                       INFORME DEL DOCENTE (Markdown)
              encabezado · lo que se le da bien · lo que le cuesta ·
              qué hacer en el aula · nota "no es un diagnóstico"
```

Implementación: `explain/plain_language.py` (orquestador) + `explain/phrases.py`
(banco de frases) + `explain/suggestions.py` (actividades) + `explain/report.py`
(ensamblado y separación docente / técnico).

---

## 3. Los 6 indicadores traducidos

| indicador (interno) | nombre para el docente | criterio CUMANIN‑2 | ejemplo de "cómo se ve" (severidad moderada) | actividad |
|---|---|---|---|---|
| `precision_modelo` | Parecido general con el modelo | similitud global | "El dibujo recuerda al modelo, pero hay que fijarse para reconocerlo." | copiar figuras grandes con el modelo al lado |
| `vertices` | Esquinas de la figura | nº de ángulos | "El cuadrado parece un óvalo, o aparecen puntas de más." | unir puntos marcados en las esquinas |
| `error_angular` | Inclinación de los ángulos | tolerancia angular | "Una cruz cuyos brazos no forman ángulos rectos." | repasar esquinas con plantilla, parar en cada vértice |
| `cierre` | Cierre de las figuras | cierre de la figura | "Cuadrados o rombos con un lado que no cierra." | laberintos y caminos cerrados; rodear siluetas |
| `intersecciones` | Cruce de líneas | respeto de intersecciones | "En la cruz, las líneas se cruzan lejos del centro." | trazar cruces sobre un punto central de color |
| `proporcion` | Tamaño de las partes | proporción | "Una cruz con un brazo largo y otro muy corto." | copiar sobre papel cuadriculado contando cuadrados |

Banco completo (leve / moderada / marcada) en `explain/phrases.py`.

---

## 4. Encabezados de resultado (sin cifras)

| acción | mensaje |
|---|---|
| `ninguna` (T ≥ 41) | "El desempeño grafomotor de **{nombre}** es **adecuado para su edad**. No se observan señales de alerta." |
| `reforzar_y_revaluar` (T 31–40) | "Conviene **prestar atención**: {nombre} muestra un desempeño **por debajo de lo esperado**. Reforzar en el aula y volver a evaluar en unas semanas." |
| `derivar` (T ≤ 30) | "**Se recomienda derivar** a {nombre} a una evaluación con un especialista. Su desempeño está **bastante por debajo** de lo esperado." |

Siempre se cierra con: *"Este informe es una ayuda para el docente, no un diagnóstico."*

---

## 5. Incertidumbre

- `confianza_media` de la sesión = media de `|prob − 0.5|·2` sobre las figuras.
- Si `< umbral_confianza_baja` (config, 0.60) → el informe empieza con:
  *"⚠️ El sistema tuvo dificultad para leer con claridad algunas figuras…
  Revisa este informe con cuidado y, si puedes, repite las fotos."*
- `preprocessing` marca por figura: "foto poco nítida", "el registro con la plantilla
  no convergió" → se listan en el panel técnico.

---

## 6. Ejemplo de informe generado (caso "en riesgo")

```
## Informe grafomotor — Ana

Conviene **prestar atención**: Ana muestra un desempeño grafomotor **por debajo de lo
esperado** para su edad. Se recomienda reforzarlo en el aula y volver a evaluarlo dentro
de unas semanas.

### Lo que se le da bien
- Mantiene bien la forma de las figuras: no le sobran ni le faltan esquinas. Se ve sobre
  todo en el/la cuadrado y en el/la triángulo.

### Lo que le cuesta más
- **Cierre de las figuras** (moderada). Le cuesta hacer que las líneas se encuentren:
  varias figuras quedan abiertas. Cómo se ve en la hoja: cuadrados o rombos con un lado
  que no cierra. Se ve sobre todo en el/la rombo y en el/la cuadrado.
- **Inclinación de los ángulos** (leve). Hace las esquinas, pero con una inclinación algo
  distinta a la del modelo. Cómo se ve en la hoja: un rombo que sale más 'tumbado'.

### Qué puedes hacer en el aula
- Laberintos y caminos cerrados donde tiene que 'volver a la puerta' sin dejar huecos.
- Rodear objetos y siluetas haciendo que la línea llegue hasta el punto de partida.
- Repasar esquinas con una plantilla o escuadra de cartón, parando en cada vértice.

---
_Este informe es una ayuda para el docente, no un diagnóstico. La decisión final
corresponde a un profesional (psicólogo o especialista)._
```

Genera este texto:  `python scripts/05_explicar_demo.py --simular --nivel reforzar_y_revaluar`

---

## 7. Cómo se valida la explicación

**Automático (en el CI):** `tests/test_plain_language.py`
- `contiene_jerga()` sobre el texto del docente → debe ser `[]`.
- Hay encabezado de resultado y sección "Qué puedes hacer".
- Ninguna frase supera ~35 palabras.
- Las cifras del panel técnico **no** aparecen en el texto del docente.

**Con docentes reales (parte del estudio de validación):**
- Comprensibilidad: tras leer el informe, el docente resume con sus palabras qué le pasa
  al niño y qué haría (comparar con la intención del informe).
- Utilidad y accionabilidad: escala tipo Likert + una pregunta abierta.
- Tiempo de lectura y dudas planteadas.
- Cuestionario SUS para la app.

---

## 8. Pulido opcional por LLM (desactivado)

`explain/llm_polish.py` deja el punto de extensión: reformular el informe con un LLM
para un español aún más natural, con un *system prompt* estricto ("no inventes datos,
no cambies cifras ni recomendaciones, sin tecnicismos"). Para la tesis se mantiene
**apagado** (`explicacion.pulido_llm.activar: false`) por reproducibilidad; si se activa,
la salida debe volver a pasar por `contiene_jerga()`.
