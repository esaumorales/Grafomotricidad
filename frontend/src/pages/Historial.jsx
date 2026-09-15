import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import Layout from '../components/Layout'
import { Cargando, ErrorConReintento } from '../components/Estado'
import { IconBuscar } from '../components/icons'
import { listarSesiones } from '../api'

const AVATAR_COLORES = [
  { bg: 'var(--peach-light)', color: 'var(--peach-dark)' },
  { bg: 'var(--sky-light)', color: 'var(--sky-dark)' },
]

function iniciales(nombre) {
  return nombre.split(' ').filter(Boolean).slice(0, 2).map((p) => p[0].toUpperCase()).join('')
}

function fechaCorta(iso) {
  return new Date(iso).toLocaleDateString('es-PE', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function Historial() {
  const [sesiones, setSesiones] = useState(null)
  const [error, setError] = useState(null)
  const [busqueda, setBusqueda] = useState('')

  const cargar = useCallback(() => {
    setError(null)
    listarSesiones().then(setSesiones).catch((e) => setError(e.message))
  }, [])

  useEffect(cargar, [cargar])

  const filtradas = useMemo(() => {
    if (!sesiones) return []
    const q = busqueda.trim().toLowerCase()
    if (!q) return sesiones
    return sesiones.filter(
      (s) => s.child_id.toLowerCase().includes(q) || (s.nombre_nino || '').toLowerCase().includes(q)
    )
  }, [sesiones, busqueda])

  return (
    <Layout>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <h1 style={{ fontSize: 32 }}>Historial de evaluaciones</h1>
          <p style={{ margin: '6px 0 0', color: 'var(--text-muted)', fontSize: 15 }}>
            Vuelve a ver el informe de cualquier evaluación anterior.
          </p>
        </div>
        <div className="historial-busqueda" style={{ display: 'flex', alignItems: 'center', gap: 10, background: 'var(--surface)', border: '2px solid var(--border)', borderRadius: 99, padding: '11px 18px' }}>
          <IconBuscar stroke="var(--text-muted)" aria-hidden="true" />
          <label htmlFor="busqueda-historial" className="visually-hidden">Buscar por nombre o código</label>
          <input
            id="busqueda-historial"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            placeholder="Buscar por nombre o código…"
            style={{ border: 'none', outline: 'none', background: 'transparent', fontSize: 14, fontWeight: 600, width: '100%' }}
          />
        </div>
      </div>

      {error && <ErrorConReintento mensaje={error} onReintentar={cargar} />}
      {!error && !sesiones && <Cargando filas={4} />}

      {sesiones && sesiones.length === 0 && (
        <div className="card" style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
          Todavía no hay evaluaciones. Empieza una desde "Nueva evaluación".
        </div>
      )}

      {sesiones && sesiones.length > 0 && (
        <div className="card no-scroll-x" style={{ padding: '14px 18px' }}>
          <div className="historial-fila" style={{ color: 'var(--text-muted)', fontSize: 12, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '.03em', padding: '6px 18px 14px' }}>
            <span />
            <span>Niño / a</span>
            <span className="col-edad">Edad</span>
            <span className="col-fecha">Fecha</span>
            <span>Nivel</span>
            <span className="col-accion" />
          </div>

          {filtradas.map((s, i) => {
            const nombre = s.nombre_nino || s.child_id
            const av = AVATAR_COLORES[i % 2]
            const adecuado = s.accion === 'ninguna'
            return (
              <Link
                key={s.id}
                to={`/informe/${s.id}`}
                className="historial-fila"
                style={{ padding: '16px 18px', borderRadius: 'var(--radius-md)', color: 'var(--text)' }}
              >
                <div aria-hidden="true" style={{ width: 40, height: 40, borderRadius: '50%', background: av.bg, color: av.color, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontFamily: "'Baloo 2'", fontSize: 13, flexShrink: 0 }}>
                  {iniciales(nombre)}
                </div>
                <div>
                  <div style={{ fontWeight: 800, fontSize: 14.5 }}>{nombre}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{s.child_id}</div>
                </div>
                <div className="col-edad" style={{ fontSize: 14, color: 'var(--text-muted)', fontWeight: 700 }}>
                  {Math.floor(s.edad_meses / 12)} a. {s.edad_meses % 12} m.
                </div>
                <div className="col-fecha" style={{ fontSize: 14, color: 'var(--text-muted)', fontWeight: 700 }}>{fechaCorta(s.fecha)}</div>
                <div>
                  <span className="badge-pill" style={{ background: adecuado ? 'var(--mint-light)' : 'var(--yellow-light)', color: adecuado ? 'var(--mint-dark)' : 'var(--yellow-dark)' }}>
                    {s.nivel}
                  </span>
                </div>
                <span className="col-accion" style={{ fontWeight: 800, fontSize: 13.5, textAlign: 'right' }}>Ver informe →</span>
              </Link>
            )
          })}
        </div>
      )}
    </Layout>
  )
}
