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
  const anterior = sesion.figuras[idx - 1]
  const siguiente = sesion.figuras[idx + 1]

  return (
    <Layout>
      <div>
        <Link to={`/informe/${sesion.id}`} style={{ fontSize: 13, fontWeight: 800, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <IconFlechaIzq /> Volver al informe
        </Link>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 10, flexWrap: 'wrap', gap: 12 }}>
          <h1 style={{ fontSize: 28 }}>Comparar figura · {sesion.nombre_nino || sesion.child_id}</h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, background: 'var(--surface)', borderRadius: 99, padding: '8px 10px', boxShadow: 'var(--shadow)' }}>
            <BotonNav
              disabled={!anterior}
              etiqueta="Figura anterior"
              onClick={() => anterior && navigate(`/comparar/${id}/${anterior.figura_id}`)}
            >
              <IconFlechaIzq stroke="var(--peach-dark)" aria-hidden="true" />
            </BotonNav>
            <div style={{ fontWeight: 800, fontSize: 14 }} aria-live="polite">Figura {idx + 1} de {sesion.figuras.length}</div>
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

      <div>
        <span className="badge-pill" style={{ background: lograda ? 'var(--mint-light)' : 'var(--yellow-light)', color: lograda ? 'var(--mint-dark)' : 'var(--yellow-dark)' }}>
          {figura.nombre} · {lograda ? 'Lograda' : 'Necesita apoyo'}
        </span>
      </div>

      <div className="comparar-grid">
        <div className="comparar-columna">
          <div style={{ fontSize: 13, fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.03em', marginBottom: 12 }}>
            Dibujo de {sesion.nombre_nino || 'el niño / la niña'}
          </div>
          <div className="card" style={{ padding: 18, transform: 'rotate(-0.6deg)' }}>
            <div style={{ background: 'var(--bg)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', height: 420, display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
              <img src={urlImagenNino(sesion.child_id, figuraId)} alt={`Dibujo de ${sesion.nombre_nino || 'el niño / la niña'} — ${figura.nombre}`} style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
            </div>
          </div>
        </div>

        <div className="comparar-columna">
          <div style={{ fontSize: 13, fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.03em', marginBottom: 12 }}>
            Plantilla de referencia
          </div>
          <div className="card" style={{ padding: 18 }}>
            <div style={{ background: 'var(--sky-light)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border)', height: 420, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <img src={urlPlantilla(figuraId)} alt={`Plantilla de referencia — ${figura.nombre}`} style={{ maxWidth: '75%', maxHeight: '75%', objectFit: 'contain' }} />
            </div>
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
