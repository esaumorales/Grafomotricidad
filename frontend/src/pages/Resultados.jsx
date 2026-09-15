import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import Layout from '../components/Layout'
import FigureIcon from '../components/FigureIcon'
import ComparacionIA from '../components/ComparacionIA'
import { Cargando, ErrorConReintento } from '../components/Estado'
import { IconCheck, IconFlechaDer, IconFlechaIzq } from '../components/icons'
import { obtenerSesion } from '../api'

export default function Resultados() {
  const { id } = useParams()
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

  const adecuado = sesion.accion === 'ninguna'
  const tecnico = sesion.panel_tecnico.resumen
  const logradas = sesion.figuras.filter((f) => (f.puntaje_docente ?? f.puntaje) === 1).length

  return (
    <Layout>
      <div>
        <Link to="/" style={{ fontSize: 13, fontWeight: 800, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <IconFlechaIzq /> Volver
        </Link>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 14, marginTop: 10, flexWrap: 'wrap' }}>
          <h1 style={{ fontSize: 30 }}>{sesion.nombre_nino || sesion.child_id}</h1>
          <span style={{ color: 'var(--text-muted)', fontSize: 15, fontWeight: 700 }}>
            {sesion.child_id} · {Math.floor(sesion.edad_meses / 12)} años {sesion.edad_meses % 12} meses
          </span>
        </div>
      </div>

      <ComparacionIA sesion={sesion} />

      <div
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
          <div style={{ fontSize: 13, fontWeight: 800, color: adecuado ? 'var(--mint-dark)' : 'var(--yellow-dark)', textTransform: 'uppercase', letterSpacing: '.04em' }}>
            Nivel de desempeño grafomotor
          </div>
          <h2 style={{ fontSize: 32, color: adecuado ? 'var(--mint-dark)' : 'var(--yellow-dark)', marginTop: 4 }}>
            {tecnico.nivel}
          </h2>
          <div style={{ fontSize: 14, color: 'var(--text-muted)', marginTop: 6, fontWeight: 700 }}>
            {logradas} de {sesion.figuras.length} figuras copiadas correctamente
            {tecnico.percentil != null && ` · percentil ${tecnico.percentil} (tramo ${tecnico.tramo_edad})`}
          </div>
        </div>
      </div>

      <div className="card">
        <h2 style={{ fontSize: 18, marginBottom: 20 }}>Resultado por figura</h2>
        <div className="figuras-grid">
          {sesion.figuras.map((f, i) => {
            const puntaje = f.puntaje_docente ?? f.puntaje
            const lograda = puntaje === 1
            return (
              <button
                key={f.figura_id}
                onClick={() => navigate(`/comparar/${sesion.id}/${f.figura_id}`)}
                aria-label={`Figura ${i + 1}, ${f.nombre}: ${lograda ? 'lograda' : 'necesita apoyo'}. Ver comparación.`}
                style={{
                  borderRadius: 'var(--radius-md)', background: lograda ? 'var(--mint-light)' : 'var(--yellow-light)',
                  padding: 14, textAlign: 'center', cursor: 'pointer', textDecoration: 'none',
                }}
              >
                <FigureIcon figuraId={f.figura_id} color={lograda ? 'var(--mint-dark)' : 'var(--yellow-dark)'} />
                <div style={{ fontSize: 11, fontWeight: 800, marginTop: 8, color: 'var(--text)' }}>{i + 1} · {f.nombre}</div>
                {lograda ? (
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4, fontSize: 11, fontWeight: 800, color: 'var(--mint-dark)', marginTop: 4 }}>
                    <IconCheck width={11} height={11} strokeWidth={4} /> Lograda
                  </div>
                ) : (
                  <div style={{ fontSize: 11, fontWeight: 800, color: 'var(--yellow-dark)', marginTop: 4 }}>Necesita apoyo</div>
                )}
              </button>
            )
          })}
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 26 }}>
          <button className="btn-primary" onClick={() => navigate(`/informe/${sesion.id}`)}>
            Ver informe detallado
            <IconFlechaDer stroke="var(--text)" />
          </button>
        </div>
      </div>
    </Layout>
  )
}
