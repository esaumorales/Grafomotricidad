import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import Layout from '../components/Layout'
import { Cargando, ErrorConReintento } from '../components/Estado'
import { IconFlechaIzq } from '../components/icons'
import { obtenerSesion, urlImagenNino, urlPlantilla } from '../api'

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
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, background: 'var(--surface)', borderRadius: 99, padding: '8px 10px', boxShadow: 'var(--shadow)' }}>
            <BotonNav
              disabled={!anterior}
              etiqueta="Figura anterior"
              onClick={() => anterior && navigate(`/comparar/${id}/${anterior.figura_id}`)}
            >
              <IconFlechaIzq stroke="var(--peach-dark)" aria-hidden="true" />
            </BotonNav>
            <div style={{ fontWeight: 800, fontSize: 22 }} aria-live="polite">Figura {idx + 1} de {sesion.figuras.length}</div>
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
      <div className="comparison-guide-stack"><ObservacionesFigura key={`obs-${figuraId}`} sesionId={id} figuraId={figuraId} /><CriteriosManual key={figuraId} figuraId={figuraId} /></div>
      <div className="comparison-images">
      <div className="comparar-grid comparison-workspace">
        <ImageReview key={`dibujo-${figuraId}`} title="Dibujo del niño o la niña" src={urlImagenNino(sesion.child_id, figuraId)} alt={`Dibujo: ${figura.nombre}`} />
        <ImageReview key={`referencia-${figuraId}`} title="Figura de referencia" src={urlPlantilla(figuraId)} alt={`Referencia: ${figura.nombre}`} reference />
      </div>
      </div>
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

function ImageReview({ title, src, alt, reference = false }) {
  const [zoom, setZoom] = useState(1)
  const [rotation, setRotation] = useState(0)
  const [failed, setFailed] = useState(false)
  return <section className="image-review comparar-columna" aria-label={title}>
    <h2>{title}</h2>
    <p className="image-origin">{reference ? "Modelo de la figura que debía copiar. Es una recreación geométrica del proyecto, no una foto del manual." : "Fotografía del dibujo realizado por el niño o la niña."}</p>
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

function ObservacionesFigura({ sesionId, figuraId }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(false)
  useEffect(() => {
    const controller = new AbortController()
    fetch(`/api/sesiones/${encodeURIComponent(sesionId)}/figuras/${encodeURIComponent(figuraId)}/observaciones`, { signal: controller.signal })
      .then((res) => { if (!res.ok) throw new Error(); return res.json() })
      .then(setData).catch((err) => { if (err.name !== 'AbortError') setError(true) })
    return () => controller.abort()
  }, [sesionId, figuraId])
  return <section className="figure-observations" aria-labelledby="figure-observations-title">
    <span className="criteria-eyebrow">Apoyo a la revisión</span><h2 id="figure-observations-title">Observaciones de esta figura</h2>
    <p className="observation-intro">Indicios geométricos de la imagen; requieren confirmación docente. No son la causa demostrada del puntaje.</p>
    {error ? <p role="alert">No se pudo analizar la imagen. Puedes consultar los criterios del manual.</p> : !data ? <p role="status">Analizando el trazo…</p> : <>
      {data.aviso_imagen && <p className="observation-photo-warning">Imagen: {data.aviso_imagen}</p>}
      <ul>{data.observaciones.map((o) => <li key={o.titulo}><div className="observation-title"><strong>{o.titulo}</strong>{o.revisar && <span>Comprobar</span>}</div><p>{o.detalle}</p></li>)}</ul>
    </>}
  </section>
}
