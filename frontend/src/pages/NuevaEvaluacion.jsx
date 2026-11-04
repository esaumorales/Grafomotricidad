import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import Layout from '../components/Layout'
import { IconCheck, IconSubir } from '../components/icons'
import { FIGURAS } from '../figuras'
import { evaluar, evaluarHojas, sesionesDeNino } from '../api'

/**
 * Intenta leer el número de figura SOLO cuando el nombre del archivo lo dice de forma
 * inequívoca (F07.jpg, figura_7.png, fig-07.jpeg, o el archivo es solo el número: 7.jpg).
 * Las fotos reales de un celular (IMG_2026...jpg, 20260911_142033.jpg) tienen números
 * largos que no significan nada -> a propósito NO se intenta adivinar ahí, para no
 * mandar una foto cualquiera a una figura al azar. Esos casos se llenan en el orden
 * en que se soltaron/eligieron (ver asignarArchivos).
 */
function figuraDesdeNombre(nombre) {
  const base = nombre.replace(/\.[^.]+$/, '').trim()
  const patrones = [
    /^f\W*0*(\d{1,2})$/i,
    /^fig(?:ura)?\W*0*(\d{1,2})$/i,
    /^0*(\d{1,2})$/,
  ]
  for (const pat of patrones) {
    const m = base.match(pat)
    if (m) {
      const n = parseInt(m[1], 10)
      if (n >= 1 && n <= 15) return `F${String(n).padStart(2, '0')}`
    }
  }
  return null
}

// Windows deja con tipo vacío las fotos HEIC del iPhone: se reconocen también por la extensión.
const esFoto = (f) => f.type.startsWith('image/') || /\.(jpe?g|png|webp|bmp|tiff?|heic|heif)$/i.test(f.name)

const EDAD_MIN_MESES = 36 // 3 años
const EDAD_MAX_MESES = 78 // 6 años y 6 meses (fin de la Tabla B.9)

const hoyISO = () => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

/** Meses cumplidos a la fecha de evaluación (fechas AAAA-MM-DD); null si falta alguna. */
function edadEnMeses(nacimiento, evaluacion) {
  if (!nacimiento || !evaluacion) return null
  const [a, m, d] = nacimiento.split('-').map(Number)
  const [a2, m2, d2] = evaluacion.split('-').map(Number)
  return (a2 - a) * 12 + (m2 - m) - (d2 < d ? 1 : 0)
}

export default function NuevaEvaluacion() {
  const navigate = useNavigate()
  const [parametros] = useSearchParams()
  const paraMismoNino = Boolean(parametros.get('childId'))
  const [childId, setChildId] = useState(() => parametros.get('childId') || '')
  const [nombreNino, setNombreNino] = useState(() => parametros.get('nombre') || '')
  const [nacimiento, setNacimiento] = useState('')
  const [evaluacion, setEvaluacion] = useState(hoyISO())
  const [mano, setMano] = useState('D')
  const [archivos, setArchivos] = useState({}) // { F01: File, ... } (modo figura por figura)
  const [modo, setModo] = useState('hojas') // 'hojas' (3 fotos de hojas) | 'figuras' (15 fotos)
  const [hojas, setHojas] = useState([]) // File[] (modo hojas, en cualquier orden)
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState(null)
  const [fotoAQuitar, setFotoAQuitar] = useState(null)
  const quitarDialogRef = useRef(null)
  const inputMasivoRef = useRef(null)
  const inputIndividualRef = useRef({})
  const inputHojasRef = useRef(null)

  useEffect(() => {
    if (!paraMismoNino || !childId) return
    let activo = true
    sesionesDeNino(childId).then((sesiones) => {
      const guardada = [...sesiones].sort((a, b) => b.fecha.localeCompare(a.fecha)).find((s) => s.fecha_nacimiento)
      if (activo && guardada) setNacimiento((actual) => actual || guardada.fecha_nacimiento)
    }).catch(() => { /* Las fechas siguen disponibles para completarlas manualmente. */ })
    return () => { activo = false }
  }, [paraMismoNino, childId])

  const subidas = Object.keys(archivos).length
  const previewsHojas = useMemo(() => hojas.map((f) => URL.createObjectURL(f)), [hojas])

  function agregarHojas(fileList) {
    setHojas((prev) => [...prev, ...fileList.filter(esFoto)].slice(0, 3))
  }
  const previews = useMemo(() => {
    const out = {}
    for (const [fid, file] of Object.entries(archivos)) out[fid] = URL.createObjectURL(file)
    return out
  }, [archivos])

  function asignarArchivos(fileList) {
    setArchivos((prev) => {
      const next = { ...prev }
      const ocupados = new Set(Object.keys(next))
      const sinFigura = []
      for (const file of fileList) {
        const fid = figuraDesdeNombre(file.name)
        if (fid && !ocupados.has(fid)) {
          next[fid] = file
          ocupados.add(fid)
        } else {
          sinFigura.push(file)
        }
      }
      const libres = FIGURAS.map((f) => f.id).filter((id) => !ocupados.has(id))
      sinFigura.forEach((file, i) => {
        if (libres[i]) {
          next[libres[i]] = file
          ocupados.add(libres[i])
        }
      })
      return next
    })
  }

  function onDrop(e) {
    e.preventDefault()
    asignarArchivos(Array.from(e.dataTransfer.files))
  }

  function onElegirMasivo(e) {
    asignarArchivos(Array.from(e.target.files))
    e.target.value = ''
  }

  function onElegirIndividual(fid, e) {
    const file = e.target.files[0]
    if (file) setArchivos((prev) => ({ ...prev, [fid]: file }))
    e.target.value = ''
  }

  const edadMeses = edadEnMeses(nacimiento, evaluacion)
  const edadOk = edadMeses !== null && edadMeses >= EDAD_MIN_MESES && edadMeses <= EDAD_MAX_MESES
  let textoEdad = 'Indica las dos fechas para calcular la edad.'
  if (edadMeses !== null) {
    textoEdad = edadMeses < 0
      ? 'La fecha de evaluación es anterior a la de nacimiento.'
      : `Edad: ${Math.floor(edadMeses / 12)} años y ${edadMeses % 12} meses (${edadMeses} meses)`
      + (edadOk ? '' : '. Fuera del rango de la prueba: de 3 años a 6 años y 6 meses.')
  }
  const listoParaEnviar = childId.trim() && edadOk && !enviando
    && (modo === 'hojas' ? hojas.length === 3 : subidas === 15)

  async function onSubmit(e) {
    e.preventDefault()
    if (!listoParaEnviar) return
    setEnviando(true)
    setError(null)
    try {
      const fd = new FormData()
      fd.append('child_id', childId.trim())
      fd.append('fecha_nacimiento', nacimiento)
      fd.append('fecha_evaluacion', evaluacion)
      fd.append('nombre_nino', nombreNino.trim())
      let res
      if (modo === 'hojas') {
        for (const h of hojas) fd.append('hojas', h)
        res = await evaluarHojas(fd)
      } else {
        fd.append('figura_ids', FIGURAS.map((f) => f.id).join(','))
        for (const f of FIGURAS) fd.append('fotos', archivos[f.id])
        res = await evaluar(fd)
      }
      navigate(`/resultados/${res.id}`)
    } catch (err) {
      setError((err.message || 'No se pudo evaluar la sesión.').replace(/^\d+:\s*/, ''))
      setEnviando(false)
    }
  }

  const total = modo === 'hojas' ? 3 : 15
  const cantidad = modo === 'hojas' ? hojas.length : subidas
  const pendiente = !childId.trim() ? 'Completa el código del niño o la niña.'
    : !edadOk ? 'Completa las fechas y comprueba la edad.'
    : cantidad < total ? `Selecciona ${total - cantidad} ${modo === 'hojas' ? 'foto(s) de las hojas' : 'foto(s) de las figuras'} para continuar.`
    : 'Todo listo para evaluar.'

  return (
    <Layout>
      <div className="evaluation-page">
        <header className="evaluation-header">
          <h1>{paraMismoNino ? `Nueva evaluación para ${nombreNino || childId}` : 'Nueva evaluación'}</h1>
          <p>Completa los datos y añade las fotografías de la prueba.</p>
        </header>
        {paraMismoNino && <div className="repeat-evaluation-note"><div><strong>Se añadirá al seguimiento de {childId}</strong><p>Confirma la fecha de nacimiento y añade las fotos de esta evaluación.</p></div><Link to={`/ninos/${encodeURIComponent(childId)}`}>Volver al seguimiento</Link></div>}
        <form className="evaluation-form" onSubmit={onSubmit} aria-busy={enviando}>
          <section className="evaluation-section" aria-labelledby="datos-title">
            <div className="evaluation-section-heading">
              <span className="section-number" aria-hidden="true">1</span>
              <div><h2 id="datos-title">Datos del niño o la niña</h2><p>La edad se calcula a partir de las fechas.</p></div>
            </div>
            <div className="evaluation-fields">
              <Campo id="campo-child-id" label="Código del niño o la niña">
                <input id="campo-child-id" required readOnly={paraMismoNino} value={childId} onChange={(e) => setChildId(e.target.value)} aria-describedby="codigo-ayuda" />
                <span id="codigo-ayuda" className="field-help">Por ejemplo: NINO_0034</span>
              </Campo>
              <Campo id="campo-nombre" label={<>Nombre <span className="optional-label">(opcional)</span></>}>
                <input id="campo-nombre" value={nombreNino} onChange={(e) => setNombreNino(e.target.value)} aria-describedby="nombre-ayuda" />
                <span id="nombre-ayuda" className="field-help">Solo para tu referencia.</span>
              </Campo>
              <Campo id="campo-nacimiento" label="Fecha de nacimiento">
                <input id="campo-nacimiento" type="date" required value={nacimiento} max={evaluacion || undefined} onChange={(e) => setNacimiento(e.target.value)} />
              </Campo>
              <Campo id="campo-evaluacion" label="Fecha de evaluación">
                <input id="campo-evaluacion" type="date" required value={evaluacion} onChange={(e) => setEvaluacion(e.target.value)} />
              </Campo>
              <p className={`evaluation-age ${edadMeses !== null && !edadOk ? 'has-warning' : ''}`} aria-live="polite">{textoEdad}</p>
              <fieldset className="hand-field">
                <legend>Mano usada</legend>
                <div className="hand-options">
                  {['D', 'I'].map((v) => (
                    <button type="button" key={v} aria-pressed={mano === v} onClick={() => setMano(v)}>
                      {mano === v && <IconCheck width={16} height={16} aria-hidden="true" />}
                      {v === 'D' ? 'Derecha' : 'Izquierda'}
                    </button>
                  ))}
                </div>
              </fieldset>
            </div>
          </section>

          <section className="evaluation-section" aria-labelledby="fotos-title">
            <div className="evaluation-section-heading photo-heading">
              <span className="section-number" aria-hidden="true">2</span>
              <div><h2 id="fotos-title">{modo === 'hojas' ? 'Fotografías de las hojas' : 'Fotografías de las figuras'}</h2>
                <p>{modo === 'hojas' ? 'Una foto por hoja, con todos sus bordes visibles.' : 'Comprueba que cada fotografía corresponde a su figura.'}</p>
              </div>
              <span className="photo-count" role="status">{cantidad} de {total} seleccionadas</span>
            </div>
            <details className="upload-sheet-guide">
              <summary><svg width="17" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><rect x="5" y="2" width="14" height="20" rx="2"/><path d="M9 7h6M9 12h6M9 17h4"/></svg><span>Ejemplos · Así deben verse las 3 fotos</span><span className="sheet-guide-orientation">Vertical</span></summary>
              <div className="upload-photo-guide"><p>Una foto por hoja, en vertical y con los cuatro bordes visibles. Las figuras de referencia quedan a la izquierda y los trazos del niño o la niña, a la derecha.</p>
                <div className="upload-photo-guide-grid">{[1, 2, 3].map((numero) => <a key={numero} href={`/guias/foto-${numero}.png`} target="_blank" rel="noreferrer" aria-label={`Ampliar ejemplo de Foto ${numero}`}><div><strong>Foto {numero}</strong><span>Figuras {(numero - 1) * 5 + 1}–{numero * 5}</span></div><img src={`/guias/foto-${numero}.png`} alt={`Ejemplo de Foto ${numero}: hoja vertical con las figuras ${(numero - 1) * 5 + 1} a ${numero * 5}`} loading="lazy" /><span className="upload-photo-guide-open">Ampliar foto ↗</span></a>)}</div>
              </div>
            </details>
            {cantidad < total && <div className="evaluation-upload" onDragOver={(e) => e.preventDefault()} onDrop={modo === 'hojas' ? (e) => { e.preventDefault(); agregarHojas(Array.from(e.dataTransfer.files)) } : onDrop}>
              <IconSubir width={28} height={28} aria-hidden="true" />
              <div className="evaluation-upload-copy"><strong>{cantidad === 0 ? (modo === 'hojas' ? 'Sube las 3 fotos de las hojas' : 'Sube las fotos de las 15 figuras') : `Sube ${total - cantidad === 1 ? 'la foto que falta' : `las ${total - cantidad} fotos que faltan`}`}</strong>
                <p>Arrástralas aquí o selecciónalas desde tu dispositivo.</p>
              </div>
              <button type="button" className="evaluation-select" disabled={enviando || (modo === 'hojas' && hojas.length >= 3)} onClick={() => (modo === 'hojas' ? inputHojasRef : inputMasivoRef).current.click()}>Subir fotos</button>
            </div>}
            <input aria-label="Subir fotos de las hojas" ref={inputHojasRef} type="file" accept="image/*,.heic,.heif" multiple hidden onChange={(e) => { agregarHojas(Array.from(e.target.files)); e.target.value = '' }} />
            <input aria-label="Subir fotos de las figuras" ref={inputMasivoRef} type="file" accept="image/*" multiple hidden onChange={onElegirMasivo} />
            <p className="photo-guidance">{modo === 'hojas' ? 'Puedes elegirlas en cualquier orden. Al evaluar, el sistema identifica las hojas y recorta las figuras.' : 'Los nombres como F01 o figura_1 ayudan a ordenar las fotos. Revisa su ubicación antes de evaluar.'}</p>

            {modo === 'hojas' ? (hojas.length > 0 &&
              <div className="sheet-previews">
                {[0, 1, 2].map((i) => (
                  <div className={`sheet-preview ${hojas[i] ? 'is-selected' : ''}`} key={i}>
                    <div className="sheet-preview-heading"><span>Foto {i + 1}</span>{hojas[i] ? <span className="photo-state"><IconCheck width={14} height={14} aria-hidden="true" /> Seleccionada</span> : <span className="photo-state">Pendiente</span>}</div>
                    {hojas[i] ? <>
                      <div className="sheet-image"><span className="preview-fallback">Vista previa no disponible</span><img src={previewsHojas[i]} alt={`Vista previa de la foto ${i + 1}`} onError={(e) => { e.currentTarget.style.display = 'none' }} /></div>
                      <div className="sheet-filename" title={hojas[i].name}>{hojas[i].name}</div>
                      <button className="photo-remove" type="button" disabled={enviando} aria-label={`Quitar foto ${i + 1}`} onClick={() => { setFotoAQuitar(hojas[i]); quitarDialogRef.current.showModal() }}><IconPapelera />Quitar foto</button>
                    </> : <div className="sheet-empty"><svg width="36" height="44" viewBox="0 0 36 44" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><rect x="5" y="2" width="26" height="40" rx="3"/><path d="M12 14h12M12 21h12M12 28h7"/></svg><span>Aún no has subido una foto</span></div>}
                  </div>
                ))}
              </div>
            ) : (
              <div className="evaluation-figures">
                {FIGURAS.map((f) => <div className="figure-preview" key={f.id}>
                  <button className="figure-photo" type="button" disabled={enviando} onClick={() => inputIndividualRef.current[f.id]?.click()} aria-label={`${f.nombre}: ${archivos[f.id] ? 'cambiar' : 'subir'} foto`}>
                    {archivos[f.id] ? <img src={previews[f.id]} alt={`Figura ${f.numero}`} /> : <IconSubir width={24} height={24} aria-hidden="true" />}
                    <strong>{f.numero} · {f.nombre}</strong><span>{archivos[f.id] ? 'Seleccionada · Cambiar foto' : 'Subir foto'}</span>
                  </button>
                  <input ref={(el) => { inputIndividualRef.current[f.id] = el }} type="file" accept="image/*" hidden aria-label={`Foto de ${f.nombre}`} onChange={(e) => onElegirIndividual(f.id, e)} />
                </div>)}
              </div>
            )}
          </section>
          {error && <div role="alert" className="evaluation-error"><strong>No se pudo completar la evaluación</strong><p>{error}</p></div>}
          <dialog ref={quitarDialogRef} className="photo-confirm-dialog" aria-labelledby="quitar-foto-title" aria-describedby="quitar-foto-description" onClose={() => setFotoAQuitar(null)}>
            <div className="photo-confirm-heading"><IconPapelera /><h2 id="quitar-foto-title">¿Quitar esta foto?</h2></div>
            <p id="quitar-foto-description">La foto se quitará de esta evaluación. El archivo original seguirá en tu dispositivo.</p>
            {fotoAQuitar && <p className="photo-confirm-filename">{fotoAQuitar.name}</p>}
            <div className="photo-confirm-actions">
              <button type="button" className="photo-cancel" autoFocus onClick={() => quitarDialogRef.current.close()}>Conservar foto</button>
              <button type="button" className="photo-confirm-remove" onClick={() => { setHojas((prev) => prev.filter((foto) => foto !== fotoAQuitar)); quitarDialogRef.current.close() }}><IconPapelera />Sí, quitar foto</button>
            </div>
          </dialog>
          <footer className="evaluation-actions">
            <p role="status">{enviando ? 'Evaluando las fotografías. Espera un momento.' : pendiente}</p>
            <button type="submit" className="btn-primary" disabled={!listoParaEnviar}>{enviando ? 'Evaluando…' : 'Evaluar ahora'}</button>
          </footer>
        </form>
      </div>
    </Layout>
  )
}

function Campo({ id, label, children }) {
  return <div className="evaluation-field"><label htmlFor={id}>{label}</label>{children}</div>
}

function IconPapelera() {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M3 6h18M9 6V4h6v2M5 6l1 14h12l1-14M10 10v6M14 10v6"/></svg>
}
