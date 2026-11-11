import EscanerHoja from '../components/EscanerHoja'
import '../components/escaner.css'
import GuiaEvaluacion from '../components/GuiaEvaluacion'
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
  const [tipoAvatar, setTipoAvatar] = useState('')
  const [nacimiento, setNacimiento] = useState('')
  const [evaluacion, setEvaluacion] = useState(hoyISO())
  const [mano, setMano] = useState('D')
  const [archivos, setArchivos] = useState({}) // { F01: File, ... } (modo figura por figura)
  const [modo, setModo] = useState('hojas') // 'hojas' (3 fotos de hojas) | 'figuras' (15 fotos)
  const [hojas, setHojas] = useState([null, null, null]) // File[] (modo hojas, en cualquier orden)
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState(null)
  const [fotoAQuitar, setFotoAQuitar] = useState(null)
  const quitarDialogRef = useRef(null)
  const inputMasivoRef = useRef(null)
  const inputIndividualRef = useRef({})
  const inputHojasRef = useRef([])
  const galeriaHojasRef = useRef([])
  const [escaner, setEscaner] = useState(null)

  useEffect(() => {
    if (!paraMismoNino || !childId) return
    let activo = true
    sesionesDeNino(childId).then((sesiones) => {
      if (!activo) return
      const recientes = [...sesiones].sort((a, b) => b.fecha.localeCompare(a.fecha))
      const guardada = recientes.find((s) => s.fecha_nacimiento)
      const avatarGuardado = recientes.find((s) => s.tipo_avatar)
      if (guardada) setNacimiento((actual) => actual || guardada.fecha_nacimiento)
      if (avatarGuardado) setTipoAvatar((actual) => actual || avatarGuardado.tipo_avatar)
    }).catch(() => { /* Las fechas siguen disponibles para completarlas manualmente. */ })
    return () => { activo = false }
  }, [paraMismoNino, childId])

  const subidas = Object.keys(archivos).length
  const previewsHojas = useMemo(() => hojas.map((f) => f ? URL.createObjectURL(f) : null), [hojas])

  function elegirHoja(indice, event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    guardarHoja(indice, file)
  }

  function guardarHoja(indice, file) {
    if (!file) return
    if (!esFoto(file)) { setError('Selecciona una fotografía JPG, PNG o HEIC.'); return }
    setHojas((prev) => prev.map((foto, i) => i === indice ? file : foto))
    setError(null)
  }
  useEffect(() => () => previewsHojas.forEach((url) => { if (url) URL.revokeObjectURL(url) }), [previewsHojas])
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
  const listoParaEnviar = childId.trim() && tipoAvatar && edadOk && !enviando
    && (modo === 'hojas' ? hojas.filter(Boolean).length === 3 : subidas === 15)

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
      fd.append('tipo_avatar', tipoAvatar)
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
  const cantidad = modo === 'hojas' ? hojas.filter(Boolean).length : subidas
  const pendiente = !childId.trim() ? 'Completa el código del niño o la niña.'
    : !tipoAvatar ? 'Elige Niño o Niña para el avatar.'
    : !edadOk ? 'Completa las fechas y comprueba la edad.'
    : cantidad < total ? `Selecciona ${total - cantidad} ${modo === 'hojas' ? 'foto(s) de las hojas' : 'foto(s) de las figuras'} para continuar.`
    : 'Todo listo para evaluar.'

  return (
    <Layout>
      <div className="evaluation-page">
        <header className="evaluation-header">
          <div className="evaluation-title-row"><h1>{paraMismoNino ? `Nueva evaluación para ${nombreNino || childId}` : 'Nueva evaluación'}</h1><GuiaEvaluacion /></div>
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
              <Campo id="campo-nombre" label={<>Nombre o seudónimo <span className="optional-label">(opcional)</span></>}>
                <input id="campo-nombre" value={nombreNino} onChange={(e) => setNombreNino(e.target.value)} aria-describedby="nombre-ayuda" />
                <span id="nombre-ayuda" className="field-help">Puedes usar un nombre ficticio para identificarlo.</span>
              </Campo>
              <Campo id="campo-avatar" label="Género">
                <select id="campo-avatar" required value={tipoAvatar} onChange={(e) => setTipoAvatar(e.target.value)}>
                  <option value="" disabled>Selecciona una opción</option>
                  <option value="nino">Niño</option>
                  <option value="nina">Niña</option>
                </select>
              </Campo>
              <Campo id="campo-nacimiento" label="Fecha de nacimiento">
                <input id="campo-nacimiento" type="date" required value={nacimiento} max={evaluacion || undefined} onChange={(e) => setNacimiento(e.target.value)} />
              </Campo>
              <Campo id="campo-evaluacion" label="Fecha de evaluación">
                <input id="campo-evaluacion" type="date" required value={evaluacion} onChange={(e) => setEvaluacion(e.target.value)} />
              </Campo>
              <p className={`evaluation-age ${edadMeses !== null && !edadOk ? 'has-warning' : ''}`} aria-live="polite">{textoEdad}</p>
              <fieldset className="hand-field" data-guia="mano">
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
            <p className="photo-guidance">Toma una foto de cada hoja en vertical, completa y con sus cuatro bordes visibles. Usa el ejemplo de cada tarjeta para elegir la hoja correspondiente.</p>
            <div className="sheet-capture-grid">
              {[0, 1, 2].map((i) => <section className={`sheet-capture-card ${hojas[i] ? 'is-selected' : ''}`} key={i} data-guia={`foto-${i + 1}`} aria-labelledby={`foto-hoja-${i}`}>
                <div className="sheet-capture-heading"><h3 id={`foto-hoja-${i}`}>Foto {i + 1}</h3><span>Figuras {i * 5 + 1}–{(i + 1) * 5}</span></div>
                <div className="sheet-capture-image"><img src={hojas[i] ? previewsHojas[i] : `/guias/foto-${i + 1}.png`} alt={hojas[i] ? `Foto ${i + 1} seleccionada` : `Ejemplo de la hoja para Foto ${i + 1}`} /><span>{hojas[i] ? 'Tu fotografía' : 'Hoja de referencia'}</span></div>
                {hojas[i] && <><p className="sheet-capture-selected"><IconCheck width={14} height={14} aria-hidden="true" />Foto seleccionada</p><p className="sheet-filename" title={hojas[i].name}>{hojas[i].name}</p></>}
                <input ref={(el) => { inputHojasRef.current[i] = el }} type="file" accept="image/*,.heic,.heif" capture="environment" hidden aria-label={`Tomar una foto de la hoja ${i + 1}`} onChange={(event) => elegirHoja(i, event)} />
                <button type="button" className="sheet-capture-button" disabled={enviando} onClick={() => navigator.mediaDevices?.getUserMedia ? setEscaner(i) : inputHojasRef.current[i]?.click()}><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M4 6h4l2-3h4l2 3h4v14H4z"/><circle cx="12" cy="12" r="4"/></svg>{hojas[i] ? 'Volver a tomar' : 'Tomar una foto'}</button>
                <input ref={(el) => { galeriaHojasRef.current[i] = el }} type="file" accept="image/*,.heic,.heif" hidden aria-label={`Elegir foto de la hoja ${i + 1}`} onChange={(event) => elegirHoja(i, event)} />
                <button type="button" className="sheet-capture-button sheet-gallery-button" disabled={enviando} onClick={() => galeriaHojasRef.current[i]?.click()}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8.5" cy="9" r="1.5"/><path d="m3 17 5-4 3 3 4-5 6 6"/></svg>
                  Elegir de la galería
                </button>
                {hojas[i] && <button className="photo-remove" type="button" disabled={enviando} aria-label={`Quitar foto ${i + 1}`} onClick={() => { setFotoAQuitar({indice: i, name: hojas[i].name}); quitarDialogRef.current.showModal() }}><IconPapelera />Quitar foto</button>}
              </section>)}
            </div>
          </section>
          {error && <div role="alert" className="evaluation-error"><strong>No se pudo completar la evaluación</strong><p>{error}</p></div>}
          {escaner !== null && <EscanerHoja numero={escaner + 1} onClose={() => setEscaner(null)} onFile={(file) => { guardarHoja(escaner, file); setEscaner(null) }} onNative={() => { inputHojasRef.current[escaner]?.click(); setEscaner(null) }} />}
          <dialog ref={quitarDialogRef} className="photo-confirm-dialog" aria-labelledby="quitar-foto-title" aria-describedby="quitar-foto-description" onClose={() => setFotoAQuitar(null)}>
            <div className="photo-confirm-heading"><IconPapelera /><h2 id="quitar-foto-title">¿Quitar esta foto?</h2></div>
            <p id="quitar-foto-description">La foto se quitará de esta evaluación. El archivo original seguirá en tu dispositivo.</p>
            {fotoAQuitar && <p className="photo-confirm-filename">{fotoAQuitar.name}</p>}
            <div className="photo-confirm-actions">
              <button type="button" className="photo-cancel" autoFocus onClick={() => quitarDialogRef.current.close()}>Conservar foto</button>
              <button type="button" className="photo-confirm-remove" onClick={() => { setHojas((prev) => prev.map((foto, i) => i === fotoAQuitar.indice ? null : foto)); quitarDialogRef.current.close() }}><IconPapelera />Sí, quitar foto</button>
            </div>
          </dialog>
          <footer className="evaluation-actions" data-guia="evaluar">
            <p role="status">{enviando ? 'Evaluando las fotografías. Espera un momento.' : pendiente}</p>
            <button type="submit" className="btn-primary" disabled={!listoParaEnviar}>{enviando ? 'Evaluando…' : 'Evaluar ahora'}</button>
          </footer>
        </form>
      </div>
    </Layout>
  )
}

function Campo({ id, label, children }) {
  return <div className="evaluation-field" data-guia={{'campo-child-id': 'codigo', 'campo-nombre': 'nombre', 'campo-avatar': 'avatar', 'campo-nacimiento': 'nacimiento', 'campo-evaluacion': 'evaluacion'}[id]}><label htmlFor={id}>{label}</label>{children}</div>
}

function IconPapelera() {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M3 6h18M9 6V4h6v2M5 6l1 14h12l1-14M10 10v6M14 10v6"/></svg>
}
