import { Marked } from 'marked'

// Debe cubrir los 3 encabezados exactos que genera report.py:
// "Lo que se le da bien" / "Lo que le cuesta más" / "Qué puedes hacer en el aula"
const ICONOS_POR_TITULO = [
  { match: /\bbien\b/i, color: 'var(--mint-icon)', textColor: 'var(--mint-dark)', path: 'M20 6 9 17l-5-5' },
  { match: /cuesta|necesita apoyo/i, color: 'var(--yellow-dark)', textColor: 'var(--yellow-dark)', path: 'M12 9v4M12 17h.01' },
  { match: /aula/i, color: 'var(--sky-icon)', textColor: 'var(--sky-dark)', path: 'M12 2a7 7 0 0 0-4 12.7V17a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2v-2.3A7 7 0 0 0 12 2Z' },
]

const marked = new Marked({
  renderer: {
    heading({ tokens, depth }) {
      const text = this.parser.parseInline(tokens)
      if (depth !== 3) return `<h${depth}>${text}</h${depth}>`
      const spec = ICONOS_POR_TITULO.find((s) => s.match.test(text))
      const color = spec?.color ?? 'var(--peach-icon)'
      const textColor = spec?.textColor ?? 'var(--peach-dark)'
      const path = spec?.path ?? 'M12 5v14M5 12h14'
      return `
        <div class="informe-heading">
          <span class="informe-heading-icon" style="background:${color}">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="${path}"/></svg>
          </span>
          <h3 style="color:${textColor}">${text}</h3>
        </div>`
    },
  },
})

/** Renderiza el informe_docente_md (Markdown plano generado por el backend) con el
 * mismo lenguaje visual del resto de la app: encabezados con ícono según la sección. */
export default function InformeMarkdown({ markdown }) {
  const html = marked.parse(markdown)
  // eslint-disable-next-line react/no-danger -- el texto lo genera nuestro propio backend
  // a partir de plantillas fijas; el único dato del usuario que entra (nombre_nino) se
  // escapa en el servidor antes de construir este markdown (ver plain_language.py).
  return <div className="informe-md" dangerouslySetInnerHTML={{ __html: html }} />
}
