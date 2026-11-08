import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

const PASOS = [
  ['[data-guia="codigo"]', 'Identifica al niño o la niña', 'Escribe un código propio, por ejemplo NINO_0034. Usa siempre ese mismo código para añadir evaluaciones a su seguimiento.'],
  ['[data-guia="nombre"]', 'Nombre o seudónimo', 'Puedes escribir un nombre o uno ficticio para reconocerlo. Este campo es opcional; el código identifica su seguimiento.'],
  ['[data-guia="avatar"]', 'Género', 'Elige Niño o Niña para asignar un retrato ficticio al perfil.'],
  ['[data-guia="nacimiento"]', 'Fecha de nacimiento', 'Indica el día, mes y año de nacimiento. Con esta fecha se calcula la edad para la evaluación.'],
  ['[data-guia="evaluacion"]', 'Fecha de evaluación', 'Comprueba que sea la fecha en que se realizó la prueba. La edad se calcula con respecto a este día.'],
  ['[data-guia="mano"]', 'Mano usada', 'Selecciona la mano con la que realizó los trazos: derecha o izquierda.'],
  ['[data-guia="foto-1"]', 'Foto 1 · Figuras 1–5', 'Pulsa «Tomar una foto» para fotografiar esta hoja completa y en vertical. El ejemplo te ayuda a reconocerla.'],
  ['[data-guia="foto-2"]', 'Foto 2 · Figuras 6–10', 'Haz lo mismo con la segunda hoja. Cada tarjeta admite una foto. Si te equivocas, puedes usar «Cambiar foto».'],
  ['[data-guia="foto-3"]', 'Foto 3 · Figuras 11–15', 'Añade la última hoja. El borde verde indica que una foto ya está seleccionada; comprueba que se vea completa y nítida.'],
  ['[data-guia="evaluar"]', 'Evalúa y revisa el resultado', 'Cuando completes los datos y las tres fotos, se habilitará «Evaluar ahora». Después podrás consultar el informe y confirmar las figuras «Por revisar».'],
]

export default function GuiaEvaluacion() {
  const [paso, setPaso] = useState(null)
  const [rect, setRect] = useState(null)
  const panel = useRef(null)
  const inicio = useRef(null)
  const cerrar = () => { setPaso(null); setRect(null); inicio.current?.focus() }
  useEffect(() => {
    if (paso == null) return
    const target = document.querySelector(PASOS[paso][0])
    if (!target) return
    const actualizar = () => {
      const r = target.getBoundingClientRect()
      setRect({left: Math.max(4, r.left - 5), top: Math.max(4, r.top - 5), width: Math.min(r.width + 10, window.innerWidth - 8), height: r.height + 10})
    }
    target.scrollIntoView({block: 'center', behavior: 'instant'})
    // Reservar el espacio de la explicación en el teléfono.
    const r = target.getBoundingClientRect()
    const espacio = (panel.current?.getBoundingClientRect().height || 230) + 48
    const exceso = r.bottom - (window.innerHeight - espacio)
    if (exceso > 0) {
      let contenedor = target.parentElement
      while (contenedor && (!/(auto|scroll)/.test(getComputedStyle(contenedor).overflowY) || contenedor.scrollHeight <= contenedor.clientHeight)) contenedor = contenedor.parentElement
      if (contenedor) contenedor.scrollBy({top: exceso + 12, behavior: 'instant'})
      else window.scrollBy({top: exceso + 12, behavior: 'instant'})
    }
    actualizar()
    panel.current?.focus({preventScroll: true})
    window.addEventListener('resize', actualizar)
    window.addEventListener('scroll', actualizar, true)
    const observador = new ResizeObserver(actualizar)
    observador.observe(target)
    return () => { window.removeEventListener('resize', actualizar); window.removeEventListener('scroll', actualizar, true); observador.disconnect() }
  }, [paso])
  function teclas(event) {
    if (event.key === 'Escape') { event.preventDefault(); cerrar() }
    if (event.key === 'Tab') {
      const controles = [...panel.current.querySelectorAll('button:not(:disabled)')]
      const primero = controles[0], ultimo = controles[controles.length - 1]
      if (event.shiftKey && (document.activeElement === primero || document.activeElement === panel.current)) { event.preventDefault(); ultimo.focus() }
      else if (!event.shiftKey && (document.activeElement === ultimo || document.activeElement === panel.current)) { event.preventDefault(); primero.focus() }
    }
  }
  return <>
    <button ref={inicio} type="button" className="tour-start" aria-label="Guía paso a paso" onClick={() => setPaso(0)}><span aria-hidden="true">?</span><span className="tour-label">Guía paso a paso</span><span className="tour-label-short" aria-hidden="true">Guía</span></button>
    {paso != null && createPortal(<div className="evaluation-tour" onKeyDown={teclas}>
      <div className="tour-shade" aria-hidden="true" />
      {rect && <div className="tour-spotlight" style={{left: rect.left, top: rect.top, width: rect.width, height: rect.height}} aria-hidden="true" />}
      <section ref={panel} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="tour-title" aria-describedby="tour-description" className="tour-panel">
        <div className="tour-top"><span>Paso {paso + 1} de {PASOS.length}</span><button type="button" onClick={cerrar}>Saltar guía <span aria-hidden="true">×</span></button></div>
        <h2 id="tour-title">{PASOS[paso][1]}</h2><p id="tour-description">{PASOS[paso][2]}</p>
        <div className="tour-actions"><button type="button" disabled={paso === 0} onClick={() => setPaso((p) => p - 1)}>Anterior</button><button type="button" className="tour-next" onClick={() => paso === PASOS.length - 1 ? cerrar() : setPaso((p) => p + 1)}>{paso === PASOS.length - 1 ? 'Terminar guía' : 'Siguiente'}<span aria-hidden="true"> →</span></button></div>
      </section>
    </div>, document.body)}
  </>
}
