# Arquitectura de la metodología

Sistema de evaluación grafomotora infantil por **visión computacional + XGBoost**, con
una capa de **explicación en lenguaje natural para el docente**. Niños de **3 a 5 años**,
prueba **Visopercepción (Vis) del CUMANIN‑2**.

---

## 1. Vista general (flujo completo)

```mermaid
flowchart TD
    subgraph REC["1 · Recolección"]
        A1["Aplicación de la prueba<br/>Visopercepción del CUMANIN-2"] --> A2["Foto de la hoja<br/>(por figura, condiciones controladas)"]
        A1 --> A3["Puntaje 0/1 por figura<br/>del docente evaluador<br/>(criterios del manual)"]
    end

    subgraph PRE["2 · Preprocesamiento de imágenes  (OpenCV / scikit-image)"]
        B1["Orientar (EXIF)"] --> B2["Corregir perspectiva<br/>e inclinación"] --> B3["Normalizar iluminación<br/>+ contraste"] --> B4["Binarizar el trazo"] --> B5["Aislar la figura"] --> B6["Registrar a la<br/>plantilla del CUMANIN-2"]
        B6 --> BQ{{"Control de calidad<br/>(nitidez, registro OK)"}}
    end

    subgraph FEA["3 · Indicadores geométricos  (6, alineados a criterios CUMANIN-2)"]
        C1["Parecido general con el modelo"]
        C2["Esquinas de la figura"]
        C3["Inclinación de los ángulos"]
        C4["Cierre de las figuras"]
        C5["Cruce de líneas"]
        C6["Tamaño de las partes"]
        C1 & C2 & C3 & C4 & C5 & C6 --> CV["Vector de indicadores<br/>por figura"]
    end

    subgraph MOD["4 · Modelo  (XGBoost)"]
        D1["Entrenamiento:<br/>puntaje por figura 0/1"] --> D2["Grid Search +<br/>CV agrupada por niño"]
        D2 --> D3["Pesos de clase<br/>(desbalance / efecto suelo 3 años)"]
        D3 --> D4["Artefacto + manifiesto<br/>(git hash, métricas, versión de baremo)"]
    end

    subgraph SCO["5 · Scoring"]
        E1["Suma de figuras → PD"] --> E2["Baremo por tramo<br/>de 4 meses (3;0–5;11)"] --> E3["Puntuación T + percentil"] --> E4["Nivel:<br/>T≥41 Adecuado · 31–40 En riesgo · ≤30 Derivar"]
    end

    subgraph EXP["6 · Explicación  (lo central)"]
        F1["SHAP por figura"] --> F2["Agregación por sesión<br/>(qué indicadores explican el resultado)"]
        F2 --> F3["Ranking:<br/>fortalezas / dificultades"]
        F3 --> F4["Severidad + figura-ejemplo"]
        F4 --> F5["Plantillas de frase<br/>(sin jerga)"]
        F5 --> F6["Sugerencias de actividad"]
        F6 --> F7["Informe para el docente<br/>(lenguaje natural)"]
        F2 --> G1["Panel técnico<br/>(T, percentil, tabla SHAP) — especialista"]
    end

    subgraph OUT["7 · Entrega"]
        H1["App web (FastAPI):<br/>el docente sube fotos → informe"]
        H2["Estudio de validación:<br/>predicción vs docente evaluador"]
    end

    A2 --> B1
    BQ -->|OK| C1
    BQ -->|baja calidad| F0["Marca: revisar fotos"] --> F7
    CV --> D1
    CV --> P1["predicción por figura<br/>(0/1 + probabilidad)"]
    D4 --> P1
    P1 --> E1
    P1 --> F1
    E4 --> F3
    E4 --> H2
    A3 -.gold standard.-> D1
    A3 -.gold standard.-> H2
    F7 --> H1
    G1 --> H1
```

---

## 2. Flujo en tiempo de inferencia (un niño en la app)

```mermaid
sequenceDiagram
    participant Doc as Docente
    participant Web as App web (FastAPI)
    participant Svc as Servicio
    participant Pre as Preprocesamiento
    participant Fea as Indicadores
    participant Xgb as XGBoost
    participant Bar as Baremo/Nivel
    participant Shp as SHAP
    participant Nlg as Explicación NL

    Doc->>Web: sube fotos + edad + IDs de figura
    Web->>Svc: evaluar_sesion(child_id, edad, fotos)
    loop por figura
        Svc->>Pre: preprocesar_figura(foto, plantilla)
        Pre-->>Svc: figura registrada + aviso de calidad
        Svc->>Fea: extraer_indicadores(figura, plantilla)
        Fea-->>Svc: vector de 6 indicadores
        Svc->>Xgb: predecir_figura(vector)
        Xgb-->>Svc: puntaje 0/1 + probabilidad
    end
    Svc->>Bar: PD → T (tramo de edad) → nivel
    Bar-->>Svc: T, percentil, nivel, acción
    Svc->>Shp: shap_por_sesion(modelo, vectores)
    Shp-->>Svc: contribución por indicador (con signo)
    Svc->>Nlg: explicar_para_docente(sesión, nivel, shap)
    Nlg-->>Svc: informe (lenguaje natural) + panel técnico
    Svc-->>Web: informe_docente_md + panel_tecnico + figuras
    Web-->>Doc: informe legible  ·  panel técnico plegado
```

---

## 3. Componentes (paquete `grafomotor`)

```mermaid
flowchart LR
    io["io.py<br/>carga/valida etiquetas"] --> ds["model/dataset.py"]
    cfg["config.py + config.yaml"] --> todos["(todos los módulos)"]
    pre["preprocessing/<br/>pipeline.py"] --> fea["features/<br/>indicadores.py · extract.py"]
    aug["augment/<br/>label_safe.py"] --> fea
    fea --> ds --> tr["model/train.py"] --> reg["model/registry.py"]
    reg --> pred["model/predict.py"]
    pred --> sco["scoring/<br/>baremo.py · niveles.py"]
    pred --> shp["explain/shap_values.py"]
    sco --> pl["explain/plain_language.py"]
    shp --> pl
    ph["explain/phrases.py"] --> pl
    sug["explain/suggestions.py"] --> pl
    pl --> rep["explain/report.py"]
    rep --> svc["webapp/service.py"]
    pred --> svc
    svc --> api["webapp/main.py (FastAPI)"]
    ds --> ev["evaluation/<br/>metrics.py · stratified.py"]
    reg --> ev
```

---

## 4. CRISP‑DM ↔ módulos

| Fase CRISP‑DM | Aquí | Módulos |
|---|---|---|
| Comprensión del negocio | evaluación grafomotora objetiva y accesible en aula | — |
| Comprensión de los datos | `00_validar_datos.py` (desbalance, efecto suelo, tramos) | `io.py` |
| Preparación de los datos | preprocesamiento de imágenes + 6 indicadores + aumento seguro | `preprocessing/`, `features/`, `augment/` |
| Modelado | XGBoost por figura, CV agrupada por niño, Grid Search | `model/` |
| Evaluación | F1 por figura, QWK del nivel, Bland‑Altman de PD, estratificado por tramo | `evaluation/` |
| Despliegue | app web + informe en lenguaje natural para el docente | `explain/`, `webapp/` |

---

## 5. Decisiones clave

- **Target de entrenamiento = 0/1 por figura** (no el nivel global): ~1 500 etiquetas
  en vez de ~150. El nivel se **deriva** (PD → baremo por edad → T → banda del CUMANIN‑2).
- **2 clases por defecto** (Adecuado / En riesgo, corte T ≤ 40); 3 clases si "Muy bajo"
  reúne suficientes casos. Se decide con la distribución real.
- **CV agrupada por niño**: ningún niño en train y test a la vez.
- **Aumento de datos que preserva la etiqueta**: nada de rotaciones amplias ni volteos
  (cambiarían los criterios de puntuación del CUMANIN‑2).
- **Explicación determinista por plantillas** (reproducible para la tesis); *hook* de
  pulido por LLM desactivado.
- **Separación estricta**: narrativa para el docente ≠ panel técnico (T, percentil, SHAP).
