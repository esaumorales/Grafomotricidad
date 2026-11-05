import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { FIGURAS } from '../figuras'

const fecha = (valor) => new Date(valor).toLocaleDateString('es-PE', {day: 'numeric', month: 'short', year: 'numeric', timeZone: 'America/Lima'})
function estadoFigura(figura) {
  if (!figura) return null
  if (figura.puntaje_docente == null && figura.decision === 'revisar') return {y: 1, texto: 'Por revisar', color: '#987100', clase: 'review'}
  return (figura.puntaje_docente ?? figura.puntaje) === 1
    ? {y: 2, texto: 'Lograda', color: '#287547', clase: 'adequate'}
    : {y: 0, texto: 'Necesita apoyo', color: '#A33D3D', clase: 'support'}
}
export default function EvolucionFigura({ sesiones }) {
  const [figuraId, setFiguraId] = useState('F01')
  const [elegida, setElegida] = useState(null)
  const [ancho, setAncho] = useState(400)
  const plot = useRef(null)
  useEffect(() => {
    const observer = new ResizeObserver(([entry]) => setAncho(Math.max(120, entry.contentRect.width)))
    if (plot.current) observer.observe(plot.current)
    return () => observer.disconnect()
  }, [])
  const datos = useMemo(() => sesiones.map((s) => {
    const figura = s.figuras?.find((f) => f.figura_id === figuraId)
    return {...s, figura, estado: estadoFigura(figura)}
  }), [sesiones, figuraId])
  const actual = datos.find((s) => s.id === elegida) || [...datos].reverse().find((s) => s.estado) || datos[datos.length - 1]
  const w = ancho, h = 150, margen = 22
  const x = (i) => datos.length === 1 ? w / 2 : margen + (w - margen * 2) * i / Math.max(1, datos.length - 1)
  const y = (estado) => 20 + (2 - estado) * 50
  const elegir = (id) => setElegida(id)
  return <section className="tracking-chart figure-evolution" aria-labelledby="figure-evolution-title">
    <div className="tracking-section-head"><div><h2 id="figure-evolution-title">Evolución por figura</h2><p>Elige una figura y toca un punto para ver su resultado.</p></div></div>
    <label className="figure-evolution-select">Figura<select value={figuraId} onChange={(e) => {setFiguraId(e.target.value);setElegida(null)}}>{FIGURAS.map((f) => <option key={f.id} value={f.id}>Figura {f.numero} · {f.nombre}</option>)}</select></label>
    <div className="figure-evolution-chart"><div className="figure-evolution-axis" aria-hidden="true"><span>Lograda</span><span>Por revisar</span><span>Necesita apoyo</span></div><div className="figure-evolution-plot" ref={plot}>
      <svg viewBox={`0 0 ${w} ${h}`} width="100%" height={h} role="group" aria-label={`Resultados por evaluación de la figura ${Number(figuraId.slice(1))}`}>
        {[0,1,2].map((n) => <line key={n} x1="0" x2={w} y1={y(n)} y2={y(n)} stroke="var(--border)" strokeDasharray="3 5"/>)}
        {datos.map((s,i) => s.estado && <g key={s.id}>
          {i > 0 && datos[i-1].estado && <line x1={x(i-1)} x2={x(i)} y1={y(datos[i-1].estado.y)} y2={y(s.estado.y)} stroke="var(--navy)" strokeWidth="2"/>}
          <g role="button" tabIndex={0} aria-label={`Evaluación ${i+1}, ${fecha(s.fecha)}: ${s.estado.texto}`} aria-pressed={actual?.id === s.id} onClick={() => elegir(s.id)} onKeyDown={(e) => {if(e.key === 'Enter' || e.key === ' '){e.preventDefault();elegir(s.id)}}}>
            <circle cx={x(i)} cy={y(s.estado.y)} r="20" fill="transparent"/>
            {actual?.id === s.id && <circle cx={x(i)} cy={y(s.estado.y)} r="10" fill="var(--gold)"/>}
            <circle cx={x(i)} cy={y(s.estado.y)} r="5" fill={s.estado.color} stroke="white" strokeWidth="1.5"/>
            <title>{fecha(s.fecha)} · {s.estado.texto}</title>
          </g>
        </g>)}
      </svg>
      <div className="figure-evolution-dates"><span>{datos[0] && fecha(datos[0].fecha)}</span>{datos.length > 1 && <span>{fecha(datos[datos.length - 1].fecha)}</span>}</div>
    </div></div>
    <div className="figure-evolution-detail" aria-live="polite">
      <div><strong>{actual && fecha(actual.fecha)}</strong>{actual?.estado ? <><span className={`history-level ${actual.estado.clase}`}><span aria-hidden="true"/>{actual.estado.texto}</span><small>{actual.figura.puntaje_docente != null ? 'Confirmado por la profesora' : 'Resultado del modelo'}</small></> : <span>Esta evaluación no tiene datos de la figura.</span>}</div>
      {actual?.estado && <Link className="history-open" to={`/comparar/${actual.id}/${figuraId}`}>Ver figura →</Link>}
    </div>
    {datos.length > 1 && <label className="figure-evolution-session">Evaluación<select value={actual?.id ?? ''} onChange={(e) => elegir(Number(e.target.value))}>{datos.map((s,i) => <option key={s.id} value={s.id}>{i+1} · {fecha(s.fecha)} · {s.estado?.texto || 'Sin datos'}</option>)}</select></label>}
    <p className="tracking-chart-note">{datos.length === 1 ? 'Con una próxima evaluación podrás comparar cómo cambia esta figura.' : 'De la evaluación más antigua a la más reciente.'} «Por revisar» requiere confirmación docente.</p>
  </section>
}
