import NivelEducativoBadge from '../components/NivelEducativoBadge'
import { Fragment, useCallback, useEffect, useMemo, useState } from 'react'
import { Link, Navigate, useParams } from 'react-router-dom'
import Layout from '../components/Layout'
import { Cargando, ErrorConReintento } from '../components/Estado'
import { IconFlechaIzq, IconFlechaDer } from '../components/icons'
import { sesionesDeNino } from '../api'

const fechaCorta = (iso) => new Date(iso).toLocaleDateString('es-PE', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'America/Lima' })
const edadTexto = (meses) => `${Math.floor(meses / 12)} años ${meses % 12} meses`

function GraficoEvolucion({ sesiones }) {
  const datos = sesiones.filter((s) => s.percentil != null && Number.isFinite(Number(s.percentil)))
  const [elegida, setElegida] = useState(null)
  const actual = datos.find((s) => s.id === elegida) || datos[datos.length - 1]
  if (!datos.length) return <section className="tracking-chart"><h2>Evolución del percentil</h2><p>No hay percentiles disponibles para representar.</p></section>
  const w = 680, h = 230, pad = {left: 38, right: 40, top: 28, bottom: 32}
  const times = datos.map((s) => new Date(s.fecha).getTime())
  const span = times[times.length-1] - times[0]
  const x = (i) => pad.left + (w-pad.left-pad.right)*(span ? (times[i]-times[0])/span : datos.length > 1 ? i/(datos.length-1) : .5)
  const y = (v) => pad.top+(h-pad.top-pad.bottom)*(1-v/100)
  const path = datos.map((s,i) => `${i ? 'L' : 'M'}${x(i)},${y(s.percentil)}`).join(' ')
  return <section className="tracking-chart" aria-labelledby="tracking-chart-title">
    <div className="tracking-section-head"><div><h2 id="tracking-chart-title">Evolución del percentil</h2><p>Selecciona un punto para consultar la evaluación.</p></div><span className="tracking-scale">Escala de 0 a 100</span></div>
    <svg viewBox={`0 0 ${w} ${h}`} className="tracking-svg" role="group" aria-label="Percentiles por fecha de registro">
      {[0,25,50,75,100].map((v) => <g key={v}><line x1={pad.left} y1={y(v)} x2={w-pad.right} y2={y(v)} stroke="var(--border)" strokeDasharray={v === 0 ? undefined : '3 5'} /><text x={pad.left-10} y={y(v)+4} textAnchor="end" fontSize="11" fill="var(--text-muted)">{v}</text></g>)}
      {datos.length > 1 && <path d={path} fill="none" stroke="var(--navy)" strokeWidth="2.5" strokeLinejoin="round" />}
      {datos.map((s,i) => <g key={s.id} role="button" tabIndex={0} aria-label={`${fechaCorta(s.fecha)}, percentil ${s.percentil}`} aria-pressed={actual.id === s.id} onClick={() => setElegida(s.id)} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault();setElegida(s.id) } }}>
        <circle cx={x(i)} cy={y(s.percentil)} r="18" fill="transparent" />
        {actual.id === s.id && <circle cx={x(i)} cy={y(s.percentil)} r="10" fill="var(--gold)" />}
        <circle cx={x(i)} cy={y(s.percentil)} r="4.5" fill="var(--navy)" stroke="white" strokeWidth="1.5" />
        <text x={x(i)} y={y(s.percentil)-14} textAnchor="middle" fontSize="12" fontWeight="600" fill="var(--navy)">{s.percentil}</text>
      </g>)}
      <text x={pad.left} y={h-8} fontSize="11" fill="var(--text-muted)">{fechaCorta(datos[0].fecha)}</text>
      {datos.length > 1 && <text x={w-pad.right} y={h-8} textAnchor="end" fontSize="11" fill="var(--text-muted)">{fechaCorta(datos[datos.length-1].fecha)}</text>}
    </svg>
    <div className="tracking-selected" aria-live="polite"><div><strong>{fechaCorta(actual.fecha)}</strong><span>{edadTexto(actual.edad_meses)} · {actual.pd_total}/15 puntos · Percentil {actual.percentil}</span></div><Link to={`/informe/${actual.id}`}>Ver informe <IconFlechaDer width={15} height={15} aria-hidden="true" /></Link></div>
    <p className="tracking-chart-note">Las fechas corresponden al registro. El percentil se calcula según la edad de cada evaluación.</p>
  </section>
}

export default function PerfilNino({ childId: childIdProp, embedded = false }) {
  const params = useParams()
  const childId = childIdProp || params.childId
  const [sesiones, setSesiones] = useState(null)
  const [error, setError] = useState(null)
  const cargar = useCallback(() => { setError(null); sesionesDeNino(childId).then(setSesiones).catch((e) => setError(e.message)) }, [childId])
  useEffect(cargar, [cargar])
  const ordenadas = useMemo(() => [...(sesiones || [])].sort((a,b) => a.fecha.localeCompare(b.fecha)), [sesiones])
  const ultima = ordenadas[ordenadas.length-1]
  const nombre = ultima?.nombre_nino || ordenadas.find((s) => s.nombre_nino)?.nombre_nino || childId
  if (!embedded && ultima) return <Navigate to={`/seguimiento/${ultima.id}`} replace />
  const Container = embedded ? Fragment : Layout
  return <Container><div className="tracking-page">
    {!embedded && <header className="tracking-header"><Link className="report-back" to="/historial"><IconFlechaIzq aria-hidden="true" />Volver al historial</Link><div className="tracking-header-row"><div><h1>Seguimiento de {nombre}</h1><p>Código: {childId}</p></div><Link className="history-new" to={`/?${new URLSearchParams({childId, nombre: ultima?.nombre_nino || ordenadas.find((s) => s.nombre_nino)?.nombre_nino || ''}).toString()}`}>+ Evaluar de nuevo</Link></div></header>}
    {error && <ErrorConReintento mensaje={error} onReintentar={cargar} />}
    {!error && !sesiones && <Cargando filas={4} />}
    {!error && sesiones && !ordenadas.length && <div className="history-empty"><h2>Aún no hay evaluaciones</h2><p>Las evaluaciones de este código aparecerán aquí.</p><Link to="/">Nueva evaluación</Link></div>}
    {!error && ultima && <>
      {embedded && <div className="tracking-embedded-top"><div><h2>Seguimiento de {nombre}</h2><p>Evaluaciones del mismo niño o niña.</p></div><Link className="history-new" to={`/?${new URLSearchParams({childId, nombre: ultima?.nombre_nino || ordenadas.find((s) => s.nombre_nino)?.nombre_nino || ''}).toString()}`}>+ Evaluar de nuevo</Link></div>}
      <div className="tracking-summary"><div><span>Evaluaciones registradas</span><strong>{ordenadas.length}</strong></div><div><span>Último registro</span><strong>{fechaCorta(ultima.fecha)}</strong></div><div><span>Último nivel registrado</span><NivelEducativoBadge percentil={ultima.percentil} /></div></div>
      <GraficoEvolucion sesiones={ordenadas} />
      <section className="tracking-records" aria-labelledby="tracking-records-title"><div className="tracking-section-head"><div><h2 id="tracking-records-title">Evaluaciones registradas</h2><p>De la más reciente a la más antigua.</p></div><span className="tracking-scale">{ordenadas.length} registros</span></div>
        <ol>{[...ordenadas].reverse().map((s) => <li key={s.id}><div className="tracking-record-date"><strong>{fechaCorta(s.fecha)}</strong><span>{edadTexto(s.edad_meses)}</span></div><div className="tracking-record-score"><strong>{s.pd_total}<small> / 15</small></strong><span>puntos</span></div><div className="tracking-record-score"><strong>{s.percentil ?? '—'}</strong><span>percentil</span></div><NivelEducativoBadge percentil={s.percentil} /><div className="tracking-record-actions"><Link className="history-open" to={`/resultados/${s.id}`}>Resultados</Link><Link className="history-open" to={`/informe/${s.id}`}>Ver informe <IconFlechaDer width={15} height={15} aria-hidden="true" /></Link></div></li>)}</ol>
      </section>
    </>}
  </div></Container>
}
