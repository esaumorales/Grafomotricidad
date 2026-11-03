import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import Layout from '../components/Layout'
import { Cargando, ErrorConReintento } from '../components/Estado'
import { IconFlechaIzq } from '../components/icons'
import { corregirFigura, obtenerSesion, urlImagenNino, urlPlantilla } from '../api'

export default function Contraste() {
  const { id, figuraId } = useParams()
  const navigate = useNavigate()
  const [sesion, setSesion] = useState(null)
  const [error, setError] = useState(null)

  const cargar = useCallback(() => {
    setError(null)
    obtenerSesion(id).then(setSesion).catch((e) => setError(e.message))
  }, [id])

  useEffect(cargar, [cargar])

  if (error) return <Layout><ErrorConReintento mensaje={error} onReintentar={cargar} /></Layout>
  if (!sesion) return <Layout><Cargando /></Layout>

  const idx = sesion.figuras.findIndex((f) => f.figura_id === figuraId)
  const figura = sesion.figuras[idx]
  if (!figura) return <Layout><ErrorConReintento mensaje="Esa figura no está en esta sesión." /></Layout>

  const puntaje = figura.puntaje_docente ?? figura.puntaje
  const lograda = puntaje === 1
  const porRevisar = figura.decision === 'revisar' && figura.puntaje_docente == null
  const anterior = sesion.figuras[idx - 1]
  const siguiente = sesion.figuras[idx + 1]

  return (
    <Layout>
      <div>
        <Link to={`/resultados/${sesion.id}`} style={{ fontSize: 19, fontWeight: 800, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <IconFlechaIzq /> Volver a resultados
        </Link>
        <div className="comparison-page-heading">
          <div className="comparison-title-row">
            <h1 style={{ fontSize: 37 }}>Comparar figura · {sesion.nombre_nino || sesion.child_id}</h1>
            <span className={`comparison-status ${porRevisar ? 'status-review' : lograda ? 'status-achieved' : 'status-support'}`}>
              <span className="status-dot" aria-hidden="true" />{figura.nombre} · {porRevisar ? 'Por revisar' : lograda ? 'Lograda' : 'Necesita apoyo'}
            </span>
          </div>
          <div className="figure-navigation-controls">
            <BotonNav
              disabled={!anterior}
              etiqueta="Figura anterior"
              onClick={() => anterior && navigate(`/comparar/${id}/${anterior.figura_id}`)}
            >
              <IconFlechaIzq stroke="var(--peach-dark)" aria-hidden="true" />
            </BotonNav>
            <div className="figure-navigation-count" aria-live="polite">Figura {idx + 1} de {sesion.figuras.length}</div>
            <BotonNav
              disabled={!siguiente}
              activo
              etiqueta="Figura siguiente"
              onClick={() => siguiente && navigate(`/comparar/${id}/${siguiente.figura_id}`)}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6" /></svg>
            </BotonNav>
          </div>
        </div>
      </div>

      <div className="comparison-layout">
      <div className="comparison-images">
      <div className="comparar-grid comparison-workspace">
        <ImageReview key={`dibujo-${figuraId}`} title="Trazo del niño o la niña" src={urlImagenNino(sesion.child_id, figuraId)} alt={`Trazo: ${figura.nombre}`}><FichaFigura key={`ficha-${figuraId}`} sesionId={id} figuraId={figuraId} figura={figura} /></ImageReview>
        <ImageReview key={`referencia-${figuraId}`} title="Figura de referencia" src={urlPlantilla(figuraId)} alt={`Referencia: ${figura.nombre}`} reference><ExplicacionFigura key={`explicacion-${figuraId}`} sesionId={sesion.id} figura={figura} /></ImageReview>
      </div>
      </div>
      <div className="comparison-guide-stack"><CriteriosManual key={figuraId} figuraId={figuraId} /><RevisionDocente key={`revision-${figuraId}`} sesionId={sesion.id} figura={figura} onGuardar={setSesion} /></div>
      </div>
    </Layout>
  )
}

function BotonNav({ children, disabled, activo, etiqueta, onClick }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      aria-label={etiqueta}
      style={{
        width: 34, height: 34, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: activo ? 'var(--peach-icon)' : 'var(--peach-light)', flexShrink: 0,
      }}
    >
      {children}
    </button>
  )
}

function ImageReview({ title, src, alt, reference = false, children }) {
  const [zoom, setZoom] = useState(1)
  const [rotation, setRotation] = useState(0)
  const [failed, setFailed] = useState(false)
  return <section className={`image-review comparar-columna ${reference ? 'reference-review' : 'drawing-review'}`} aria-label={title}>
    <div className="image-review-main">
    <h2>{title}</h2>
    <p className="image-origin">{reference ? "Modelo de la figura que debía copiar. Es una recreación geométrica del proyecto, no una foto del manual." : "Fotografía del trazo realizado por el niño o la niña."}</p>
    <div className="image-tools" role="group" aria-label={`Ajustar ${title.toLowerCase()}`}>
      <button type="button" aria-label={`Alejar ${title.toLowerCase()}`} disabled={zoom <= 1} onClick={() => setZoom((v) => Math.max(1, v - .25))}>−</button>
      <output aria-label="Ampliación">{Math.round(zoom * 100)} %</output>
      <button type="button" aria-label={`Ampliar ${title.toLowerCase()}`} disabled={zoom >= 3} onClick={() => setZoom((v) => Math.min(3, v + .25))}>+</button>
      <button type="button" onClick={() => setRotation((v) => (v + 90) % 360)}><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M20 11a8 8 0 1 1-3-6M20 3v6h-6"/></svg>Girar {rotation > 0 && `(${rotation}°)`}</button>
      <button type="button" disabled={zoom === 1 && rotation === 0} onClick={() => { setZoom(1); setRotation(0) }}>Restablecer</button>
    </div>
    <div className={`image-review-viewport ${zoom === 1 ? 'is-fitted' : 'is-zoomed'}`} tabIndex={0} role="region" aria-label={`${title}, área desplazable`}>
      {failed ? <p role="status">No se pudo cargar la imagen.</p> : <div className="image-review-canvas" style={{width: `${zoom * 100}%`}}><img className={reference ? 'reference-display' : ''} src={src} alt={alt} onError={() => setFailed(true)} style={{transform: `rotate(${rotation}deg)`}} /></div>}
    </div>
    </div>
    {children}
  </section>
}

function CriteriosManual({ figuraId }) {
  const [criterios, setCriterios] = useState(null)
  const [abierto, setAbierto] = useState(() => window.matchMedia('(min-width: 1180px)').matches)
  const [error, setError] = useState(false)
  useEffect(() => {
    const controller = new AbortController()
    fetch(`/api/criterios/${encodeURIComponent(figuraId)}`, { signal: controller.signal })
      .then((res) => { if (!res.ok) throw new Error('No disponible'); return res.json() })
      .then((data) => setCriterios(data.criterios))
      .catch((err) => { if (err.name !== 'AbortError') setError(true) })
    return () => controller.abort()
  }, [figuraId])
  return <details className="manual-criteria criteria-guide" open={abierto} onToggle={(e) => setAbierto(e.currentTarget.open)}>
    <summary><span><span className="criteria-eyebrow">Guía de revisión · Figura {Number(figuraId.slice(1))}</span><strong>Criterios del manual</strong></span><svg className="criteria-chevron" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg></summary>
    <div className="criteria-content"><p className="manual-criteria-note">Consulta estos criterios mientras comparas las imágenes.</p>
    {error ? <p role="alert">No se pudieron cargar los criterios.</p> : criterios === null ? <p role="status">Cargando criterios…</p> : criterios.length ? <ol type="a">{criterios.map((texto, i) => <li key={i}>{texto}</li>)}</ol> : <p>Los criterios de esta figura están pendientes de incorporar.</p>}
  </div></details>
}

function FichaFigura({ sesionId, figuraId, figura }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(false)
  useEffect(() => {
    const controller = new AbortController()
    fetch(`/api/sesiones/${encodeURIComponent(sesionId)}/figuras/${encodeURIComponent(figuraId)}/observaciones`, { signal: controller.signal })
      .then((res) => { if (!res.ok) throw new Error(); return res.json() })
      .then(setData).catch((err) => { if (err.name !== 'AbortError') setError(true) })
    return () => controller.abort()
  }, [sesionId, figuraId])
  const pendiente = figura.decision === 'revisar' && figura.puntaje_docente == null
  const lograda = (figura.puntaje_docente ?? figura.puntaje) === 1
  const docente = figura.puntaje_docente != null
  const estado = pendiente ? 'review' : lograda ? 'achieved' : 'support'
  const medicion = data?.observaciones.find((o) => o.fuente === 'medicion' && o.detalle_tecnico)
  const cerrada = ['F04','F05','F06','F09','F10','F11','F15'].includes(figuraId)
  return <section className="figure-reading-card" aria-labelledby="figure-reading-title">
    <h3 id="figure-reading-title">Lectura de esta figura</h3>
    <div className={`figure-reading-result ${estado}`}>
      <span className="reading-symbol" aria-hidden="true">{pendiente ? '?' : lograda ? '✓' : '!'}</span>
      <div><strong>{pendiente ? 'Por revisar' : lograda ? 'Lograda' : 'Necesita apoyo'}</strong><span>{docente ? 'Resultado confirmado por la docente' : 'Resultado del modelo'}</span></div>
    </div>
    {pendiente && <p className="reading-pending">Confirma el puntaje con los criterios del manual.</p>}
    <h4>Aspectos del trazo</h4>
    {!data && !error ? <p role="status" className="reading-note">Consultando la imagen…</p> : <>
      <dl className="reading-aspects">
        {['F01','F02'].includes(figuraId) && <FilaAspecto nombre="Inclinación" estado={medicion ? medicion.revisar ? 'review' : 'achieved' : 'unknown'} texto={medicion ? (medicion.revisar ? 'Conviene comprobarla' : 'Dentro de lo permitido') : 'Sin información suficiente'} falta={!medicion} />}
        <FilaAspecto nombre="Forma y trazos" estado="manual" texto="Por confirmar por la profesora" />
        {cerrada && <FilaAspecto nombre="Cierre" estado="unknown" texto="Sin comprobación automática" />}
      </dl>
      {(error || data?.observaciones.some((o) => o.fuente === 'limitacion')) && <p className="reading-note">No se pudieron obtener medidas fiables de la foto. Esto no cambia el resultado del modelo.</p>}
      {medicion?.detalle_tecnico && <details className="reading-details"><summary>Ver medida de inclinación</summary><p>{medicion.detalle_tecnico}</p><p>{medicion.detalle}</p></details>}
    </>}
    <p className="reading-key"><span aria-hidden="true">○</span> Gris: requiere revisión visual, no significa que esté mal.</p>
  </section>
}

function FilaAspecto({ nombre, estado, texto, falta = false }) {
  return <div className="reading-aspect"><dt>{nombre}</dt><dd className={`reading-aspect-status ${falta ? 'unknown' : estado}`}><span aria-hidden="true">{falta ? '—' : estado === 'achieved' ? '✓' : estado === 'review' ? '!' : '○'}</span>{falta ? 'Sin información suficiente' : texto}</dd></div>
}

function RevisionDocente({ sesionId, figura, onGuardar }) {
  const [seleccion, setSeleccion] = useState(figura.puntaje_docente)
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState(null)
  const [guardado, setGuardado] = useState(false)
  const revisada = figura.puntaje_docente != null
  const cambio = seleccion != null && (!revisada || seleccion !== figura.puntaje_docente)
  async function guardar() {
    if (!cambio || guardando) return
    setGuardando(true); setError(null); setGuardado(false)
    try {
      const resultado = await corregirFigura(sesionId, figura.figura_id, seleccion)
      onGuardar(resultado); setGuardado(true)
    } catch {
      setError('No se pudo guardar. Tu selección sigue aquí; intenta de nuevo.')
    } finally { setGuardando(false) }
  }
  return <section className="teacher-review-card" aria-labelledby="teacher-review-title">
    <div className="teacher-review-heading"><h3 id="teacher-review-title">Revisión de la profesora</h3><span className={`teacher-review-state ${revisada ? 'is-reviewed' : ''}`}>{revisada ? 'Revisada' : 'Sin revisar'}</span></div>
    <p>Compara el trazo con la referencia y los criterios del manual. Después, confirma tu valoración.</p>
    <div className="teacher-review-options" role="group" aria-label="Valoración de la profesora">
      <button type="button" disabled={guardando} aria-pressed={seleccion === 1} className="teacher-choice choice-achieved" onClick={() => { setSeleccion(1);setGuardado(false) }}><span aria-hidden="true">✓</span><span>Lograda</span></button>
      <button type="button" disabled={guardando} aria-pressed={seleccion === 0} className="teacher-choice choice-support" onClick={() => { setSeleccion(0);setGuardado(false) }}><span aria-hidden="true">!</span><span>Necesita apoyo</span></button>
    </div>
    <div className="teacher-review-save"><span>{cambio ? 'Cambio pendiente de guardar' : revisada ? 'Valoración guardada' : 'Selecciona una opción'}</span><button type="button" disabled={!cambio || guardando} onClick={guardar}>{guardando ? 'Guardando…' : 'Guardar revisión'}</button></div>
    {guardado && <p role="status" className="teacher-review-success">Revisión guardada. La puntuación de la sesión se ha actualizado.</p>}
    {error && <p role="alert" className="teacher-review-error">{error}</p>}
    <p className="teacher-review-note">Se guarda tu valoración sin borrar la predicción original del modelo.</p>
  </section>
}

const FORMAS_ESPERADAS = {
  F01: 'una sola línea recta en posición vertical',
  F02: 'dos líneas horizontales que no se juntan ni forman curvas',
  F03: 'dos líneas que se cruzan sin quedar separadas en el punto de encuentro',
  F04: 'un contorno cerrado, redondo u ovalado, sin esquinas ni lados rectos',
  F05: 'un contorno cerrado de cuatro lados, con cuatro esquinas aproximadamente rectas',
  F06: 'un contorno cerrado de tres lados y tres puntas, sin líneas onduladas',
  F07: 'dos líneas que forman una X y se cruzan por dentro, no en sus extremos',
  F08: 'una línea continua con las dos ondulaciones del modelo',
  F09: 'un contorno cerrado de cuatro lados con dos líneas que se cruzan dentro y llegan a las esquinas según el manual',
  F10: 'una figura cerrada de cuatro lados apoyada sobre una punta',
  F11: 'un círculo arriba y un triángulo abajo que se tocan sin cruzarse',
  F12: 'una línea recta y una curva que se tocan en un punto sin superponerse',
  F13: 'dos curvas que se tocan por el centro, por su lado convexo, sin superponerse',
  F14: 'dos rectas que se unen arriba y una curva de tres ondas que cruza ambas rectas',
  F15: 'un cuadrado arriba y un círculo abajo a la derecha que se cruzan en dos puntos, con una sola esquina del cuadrado dentro del círculo',
}

function ExplicacionFigura({ sesionId, figura }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(false)
  useEffect(() => {
    const controller = new AbortController()
    fetch(`/api/sesiones/${encodeURIComponent(sesionId)}/figuras/${encodeURIComponent(figura.figura_id)}/observaciones`, { signal: controller.signal })
      .then((res) => { if (!res.ok) throw new Error(); return res.json() })
      .then(setData).catch((err) => { if (err.name !== 'AbortError') setError(true) })
    return () => controller.abort()
  }, [sesionId, figura.figura_id])
  const docente = figura.puntaje_docente != null
  const pendiente = !docente && figura.decision === 'revisar'
  const lograda = (figura.puntaje_docente ?? figura.puntaje) === 1
  const esperada = FORMAS_ESPERADAS[figura.figura_id] || 'la forma indicada en el manual'
  const lectura = docente
    ? lograda
      ? 'La profesora confirmó que esta figura está lograda.'
      : 'La profesora indicó que esta figura necesita apoyo.'
    : pendiente
      ? 'Este trazo está pendiente de revisión: el sistema aún no puede decidir si la figura está lograda.'
      : lograda
        ? 'El sistema valoró esta figura como lograda.'
        : 'El sistema valoró esta figura como «Necesita apoyo».'
  const medida = data?.observaciones.find((o) => o.fuente === 'medicion' && o.detalle_tecnico)
  const limitada = data?.observaciones.some((o) => o.fuente === 'limitacion')
  return <section className="figure-paragraph-card" aria-labelledby="figure-explanation-title">
    <span className="criteria-eyebrow">Figura {Number(figura.figura_id.slice(1))} · {figura.nombre}</span>
    <h3 id="figure-explanation-title">Qué nos dice este trazo</h3>
    <p>{lectura} Para esta figura se espera {esperada}. {pendiente
      ? 'Compara el trazo con la referencia para confirmar si cumple con esa forma.'
      : lograda
        ? 'La valoración corresponde al trazo completo; los aspectos de la tabla se revisan por separado.'
        : 'Este resultado señala que conviene revisar cómo se realizó la figura, pero no identifica por sí solo qué parte hay que mejorar.'}</p>
    {medida && <p>{medida.titulo}. {medida.detalle}</p>}
    {limitada && <p className="figure-explanation-caution">En esta foto el sistema no pudo comprobar qué parte coincide o se diferencia de la referencia. Esa comparación debe hacerla la profesora.</p>}
    {!data && !error && <p role="status" className="reading-note">Consultando detalles de esta figura…</p>}
    {error && <p className="reading-note">Los detalles automáticos no están disponibles. Puedes comparar las imágenes y consultar los criterios del manual.</p>}

  </section>
}
