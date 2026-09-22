import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import Layout from '../components/Layout'
import { Cargando, ErrorConReintento } from '../components/Estado'
import { IconFlechaIzq } from '../components/icons'
import { sesionesDeNino } from '../api'

function fechaCorta(iso) {
  return new Date(iso).toLocaleDateString('es-PE', { day: 'numeric', month: 'short', year: 'numeric' })
}

function edadTexto(meses) {
  return `${Math.floor(meses / 12)} a. ${meses % 12} m.`
}

/** Gráfico de evolución (percentil a lo largo del tiempo), sin librería externa. */
function GraficoEvolucion({ sesiones }) {
  const conDato = sesiones.filter((s) => s.percentil != null)
  if (conDato.length < 2) return null

  const w = 640
  const h = 200
  const pad = { top: 20, right: 20, bottom: 34, left: 36 }
  const innerW = w - pad.left - pad.right
  const innerH = h - pad.top - pad.bottom

  const x = (i) => pad.left + (innerW * i) / (conDato.length - 1)
  const y = (pc) => pad.top + innerH * (1 - pc / 100)

  const puntos = conDato.map((s, i) => [x(i), y(s.percentil)])
  const linea = puntos.map(([px, py], i) => `${i === 0 ? 'M' : 'L'}${px.toFixed(1)},${py.toFixed(1)}`).join(' ')

  // banda de riesgo: percentil <= 16 (mismo corte que scoring/niveles.py)
  const yRiesgo = y(16)

  return (
    <div className="card" style={{ padding: '22px 26px' }}>
      <div style={{ fontSize: 13, fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.03em', marginBottom: 14 }}>
        Evolución del percentil en el tiempo
      </div>
      <svg viewBox={`0 0 ${w} ${h}`} style={{ width: '100%', height: 'auto', overflow: 'visible' }} role="img" aria-label="Gráfico de evolución del percentil a lo largo de las evaluaciones">
        {/* banda de riesgo (percentil <= 16) */}
        <rect x={pad.left} y={yRiesgo} width={innerW} height={pad.top + innerH - yRiesgo} fill="var(--yellow-light)" opacity="0.6" />
        {/* eje */}
        <line x1={pad.left} y1={pad.top} x2={pad.left} y2={pad.top + innerH} stroke="var(--border)" strokeWidth="1.5" />
        <line x1={pad.left} y1={pad.top + innerH} x2={pad.left + innerW} y2={pad.top + innerH} stroke="var(--border)" strokeWidth="1.5" />
        {[0, 50, 100].map((v) => (
          <text key={v} x={pad.left - 8} y={y(v) + 4} textAnchor="end" fontSize="11" fill="var(--text-muted)">{v}</text>
        ))}
        {/* línea de evolución */}
        <path d={linea} fill="none" stroke="var(--peach-dark)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        {puntos.map(([px, py], i) => (
          <circle key={i} cx={px} cy={py} r="4.5" fill="var(--peach-dark)" stroke="var(--surface)" strokeWidth="1.5" />
        ))}
        {conDato.map((s, i) => (
          <text key={s.id} x={x(i)} y={h - 10} textAnchor="middle" fontSize="10.5" fill="var(--text-muted)">
            {fechaCorta(s.fecha).replace(/ de \d+$/, '')}
          </text>
        ))}
      </svg>
      <div style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 4 }}>
        Zona sombreada: percentil ≤ 16 (en riesgo, ver <code>scoring/niveles.py</code>).
      </div>
    </div>
  )
}

export default function PerfilNino() {
  const { childId } = useParams()
  const [sesiones, setSesiones] = useState(null)
  const [error, setError] = useState(null)

  const cargar = useCallback(() => {
    setError(null)
    sesionesDeNino(childId).then(setSesiones).catch((e) => setError(e.message))
  }, [childId])

  useEffect(cargar, [cargar])

  const nombre = useMemo(() => sesiones?.find((s) => s.nombre_nino)?.nombre_nino || childId, [sesiones, childId])

  return (
    <Layout>
      <div>
        <Link to="/historial" style={{ fontSize: 13, fontWeight: 800, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <IconFlechaIzq /> Volver al historial
        </Link>
        <h1 style={{ fontSize: 28, marginTop: 8 }}>Seguimiento de {nombre}</h1>
        <p style={{ margin: '6px 0 0', color: 'var(--text-muted)', fontSize: 15 }}>
          Código: {childId} · {sesiones ? `${sesiones.length} evaluación(es) registrada(s)` : '…'}
        </p>
      </div>

      {error && <ErrorConReintento mensaje={error} onReintentar={cargar} />}
      {!error && !sesiones && <Cargando filas={4} />}

      {sesiones && sesiones.length === 0 && (
        <div className="card" style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
          No hay evaluaciones registradas para este código todavía.
        </div>
      )}

      {sesiones && sesiones.length > 0 && (
        <>
          <GraficoEvolucion sesiones={sesiones} />
          {sesiones.length < 2 && (
            <div className="card" style={{ color: 'var(--text-muted)', fontSize: 13.5 }}>
              Todavía hay una sola evaluación — el gráfico de evolución aparece a partir de la segunda.
            </div>
          )}

          <div className="card no-scroll-x" style={{ padding: '14px 18px' }}>
            <div style={{ fontSize: 13, fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.03em', padding: '6px 18px 14px' }}>
              Línea de tiempo (de la más antigua a la más reciente)
            </div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {[...sesiones].reverse().map((s) => {
                const adecuado = s.accion === 'ninguna'
                return (
                  <Link
                    key={s.id}
                    to={`/informe/${s.id}`}
                    style={{
                      display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16,
                      padding: '14px 18px', borderRadius: 'var(--radius-md)', color: 'var(--text)',
                      borderTop: '1px solid var(--border)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                      <div style={{ fontSize: 14, fontWeight: 800, minWidth: 110 }}>{fechaCorta(s.fecha)}</div>
                      <div style={{ fontSize: 13, color: 'var(--text-muted)', fontWeight: 700 }}>{edadTexto(s.edad_meses)}</div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                      <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                        PD {s.pd_total}/15{s.percentil != null ? ` · Pc ${s.percentil}` : ''}
                      </span>
                      <span className="badge-pill" style={{ background: adecuado ? 'var(--mint-light)' : 'var(--yellow-light)', color: adecuado ? 'var(--mint-dark)' : 'var(--yellow-dark)' }}>
                        {s.nivel}
                      </span>
                      <span style={{ fontWeight: 800, fontSize: 13 }}>Ver informe →</span>
                    </div>
                  </Link>
                )
              })}
            </div>
          </div>
        </>
      )}
    </Layout>
  )
}
