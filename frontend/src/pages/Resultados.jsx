import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useEvaluacion } from '../components/EvaluacionShell'
import ComparacionIA from '../components/ComparacionIA'
import { IconCheck, IconFlechaDer } from '../components/icons'
import { urlPlantilla } from '../api'

export default function Resultados() {
  const navigate = useNavigate()
  const { sesion } = useEvaluacion()
  const [filtro, setFiltro] = useState('todas')

  const adecuado = sesion.accion === 'ninguna'
  const tecnico = sesion.panel_tecnico.resumen
  const logradas = sesion.figuras.filter((f) => (f.puntaje_docente ?? f.puntaje) === 1).length

  return (
    <>
      <ComparacionIA sesion={sesion} />

      <div
        className="result-summary"
        style={{
          background: adecuado ? 'var(--mint-light)' : 'var(--yellow-light)', borderRadius: 'var(--radius-lg)',
          padding: '32px 36px', display: 'flex', alignItems: 'center', gap: 28, flexWrap: 'wrap',
        }}
      >
        <div
          aria-hidden="true"
          style={{
            width: 88, height: 88, borderRadius: '50%', flexShrink: 0,
            background: adecuado ? 'var(--mint-icon)' : 'var(--yellow-dark)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          <IconCheck width={44} height={44} strokeWidth={2.8} stroke="white" />
        </div>
        <div>
          <div style={{ fontSize: 19, fontWeight: 800, color: adecuado ? 'var(--mint-dark)' : 'var(--yellow-dark)', textTransform: 'uppercase', letterSpacing: '.04em' }}>
            Nivel de desempeño grafomotor
          </div>
          <h2 style={{ fontSize: 43, color: adecuado ? 'var(--mint-dark)' : 'var(--yellow-dark)', marginTop: 4 }}>
            {tecnico.nivel}
          </h2>
          <div style={{ fontSize: 22, color: 'var(--text-muted)', marginTop: 6, fontWeight: 700 }}>
            {logradas} de {sesion.figuras.length} figuras copiadas correctamente
            {tecnico.percentil != null && ` · percentil ${tecnico.percentil} (tramo ${tecnico.tramo_edad})`}
          </div>
        </div>
      </div>

      <section className="figure-results" aria-labelledby="figure-results-title">
        <div className="figure-results-heading"><div><h2 id="figure-results-title">Revisar los dibujos</h2><p>Aquí se muestran las figuras de referencia. Selecciona una para compararla con el dibujo del niño o la niña.</p></div></div>
        <div className="results-toolbar">
        <div className="figure-filters" role="group" aria-label="Filtrar figuras">
          {[['todas', 'Todas'], ['revisar', 'Por revisar'], ['apoyo', 'Necesita apoyo'], ['logradas', 'Logradas']].map(([valor, etiqueta]) => {
            const contar = sesion.figuras.filter((f) => valor === 'todas' || (valor === 'revisar' ? f.decision === 'revisar' && f.puntaje_docente == null : valor === 'logradas' ? (f.puntaje_docente ?? f.puntaje) === 1 : (f.puntaje_docente ?? f.puntaje) === 0)).length
            return <button type="button" key={valor} aria-pressed={filtro === valor} onClick={() => setFiltro(valor)}>{etiqueta}<span>{contar}</span></button>
          })}
        </div>
        <div className="result-report-action"><button className="btn-primary" onClick={() => navigate(`/informe/${sesion.id}`)}>Ver informe detallado <IconFlechaDer aria-hidden="true" /></button></div>
        </div>
        <div className="result-figure-grid">
          {sesion.figuras.filter((f) => filtro === 'todas' || (filtro === 'revisar' ? f.decision === 'revisar' && f.puntaje_docente == null : filtro === 'logradas' ? (f.puntaje_docente ?? f.puntaje) === 1 : (f.puntaje_docente ?? f.puntaje) === 0)).map((f) => {
            const revisar = f.decision === 'revisar' && f.puntaje_docente == null
            const lograda = (f.puntaje_docente ?? f.puntaje) === 1
            const estado = revisar ? 'Por revisar' : lograda ? 'Lograda' : 'Necesita apoyo'
            return <Link key={f.figura_id} className="result-figure" to={`/comparar/${sesion.id}/${f.figura_id}`}>
              <div className="result-drawing"><span>Imagen no disponible</span><img loading="lazy" className="reference-display" src={urlPlantilla(f.figura_id)} alt={`Figura de referencia: ${f.nombre}`} onError={(e) => { e.currentTarget.style.display = 'none' }} /></div>
              <div className="result-figure-caption"><strong>{Number(f.figura_id.slice(1))} · {f.nombre}</strong><span className={`figure-status ${revisar || !lograda ? 'needs-review' : ''}`}>{lograda && !revisar && <IconCheck width={14} height={14} aria-hidden="true" />}{estado}</span><span className="figure-compare-link">Comparar dibujo <IconFlechaDer width={14} height={14} aria-hidden="true" /></span></div>
            </Link>
          })}
        </div>
        {sesion.figuras.filter((f) => filtro === 'todas' || (filtro === 'revisar' ? f.decision === 'revisar' && f.puntaje_docente == null : filtro === 'logradas' ? (f.puntaje_docente ?? f.puntaje) === 1 : (f.puntaje_docente ?? f.puntaje) === 0)).length === 0 && <p role="status" className="result-empty">No hay figuras en este grupo.</p>}

      </section>
    </>
  )
}
