# Diagramas de la documentación

Los dibujos de `docs/GUIA_PRINCIPIANTE.md` y del `README.md` se escriben como **texto**
([Mermaid](https://mermaid.js.org/)) en `fuentes/` y se **convierten en imágenes** (`docs/img/`,
en SVG y PNG) con un tema común (`tema.json`: colores, tipografía y espaciado).

| Archivo | Qué muestra |
|---|---|
| `01_flujo_completo` | De la hoja en papel al informe para la docente |
| `02_segmentar_hoja` | Cómo se endereza y corta una hoja |
| `03_preparar_imagenes` | Qué se genera para la técnica A y la B |
| `04_dos_tecnicas` | Las dos técnicas que se comparan |
| `05_puntaje_a_nivel` | Del puntaje al nivel del niño |
| `06_carpetas` | Dónde queda cada archivo |
| `07_estado` | Lo hecho y lo pendiente |
| `08_evaluacion_justa` | Cómo se evalúa sin hacer trampa |

## Cómo cambiar o crear un diagrama

Requiere [Node.js](https://nodejs.org/) (una sola vez: `npm install` dentro de esta carpeta).

```bash
cd docs/diagramas
npm install            # primera vez
# 1. edita o crea fuentes/<nombre>.mmd
npm run render         # regenera todas las imágenes en docs/img/
npm run render -- 02   # solo los que empiezan con 02
```

Después, en el `.md` se inserta con `![descripción](img/<nombre>.png)`.

## Reglas de estilo (para que todo se vea igual)

- **Colores con significado**, definidos con `classDef` en cada archivo:
  azul = paso normal · amarillo = parte humana o decisión · morado = técnica A ·
  verde azulado = técnica B · verde = hecho · azul oscuro = resultado final · rojo = aviso.
- **Textos cortos**: un título en negrita y una línea de explicación (`<b>Título</b><br/>detalle`).
- **Ancho moderado**: si un diagrama sale muy ancho, se parte en bloques (`subgraph` con
  `direction LR`) apilados hacia abajo. Se unen **bloque con bloque** (`S1 --> S2`), no nodo con
  nodo, para que Mermaid respete la dirección interna.
- **Sin datos de niños**: los diagramas nunca incluyen fotos ni nombres reales.
