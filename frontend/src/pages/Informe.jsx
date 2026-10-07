import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import Layout from '../components/Layout'
import InformeMarkdown from '../components/InformeMarkdown'
import ComparacionIA from '../components/ComparacionIA'
import { Cargando, ErrorConReintento } from '../components/Estado'
import { IconBarras, IconChevronAbajo, IconChevronArriba, IconComparar, IconDescargar, IconFlechaIzq, IconLapiz } from '../components/icons'
import { corregirFigura, obtenerSesion } from '../api'

const SUGERENCIA_POR_ACCION = {
  ninguna: 'No hace falta ninguna acción específica por ahora.',
  reforzar_y_revaluar: 'Reforzar en el aula y volver a evaluar en 4 a 6 semanas.',
  derivar: 'Conversar con la familia y considerar derivar a un especialista.',
}

export default function Informe() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [sesion, setSesion] = useState(null)
  const [error, setError] = useState(null)
  const [panelAbierto, setPanelAbierto] = useState(false)
  const [corrigiendo, setCorrigiendo] = useState(false)

  const cargar = useCallback(() => {
    setError(null)
    obtenerSesion(id).then(setSesion).catch((e) => setError(e.message))
  }, [id])

  useEffect(cargar, [cargar])

  if (error) return <Layout><ErrorConReintento mensaje={error} onReintentar={cargar} /></Layout>
  if (!sesion) return <Layout><Cargando filas={6} /></Layout>

  async function alternarPuntaje(figuraId, actual) {
    const nuevo = actual === 1 ? 0 : 1
    const res = await corregirFigura(sesion.id, figuraId, nuevo)
    setSesion(res)
  }

  const tecnico = sesion.panel_tecnico.resumen

  return (
    <Layout>
      <div>
        <Link to={`/resultados/${sesion.id}`} style={{ fontSize: 13, fontWeight: 800, display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <IconFlechaIzq /> Volver a resultados
        </Link>
        <h1 style={{ fontSize: 28, marginTop: 8 }}>Informe para {sesion.nombre_nino || sesion.child_id}</h1>
      </div>

      <ComparacionIA sesion={sesion} />

      <div className="informe-layout">
        <div className="informe-principal">
          <div className="card" style={{ padding: '30px 34px' }}>
            <InformeMarkdown markdown={sesion.informe_docente_md} />
          </div>

          <div style={{ background: 'var(--tech-bg)', border: '1.5px solid var(--tech-border)', borderRadius: 'var(--radius-lg)', padding: '22px 30px' }}>
            <button
              onClick={() => setPanelAbierto((v) => !v)}
              aria-expanded={panelAbierto}
              style={{ display: 'flex', width: '100%', alignItems: 'center', justifyContent: 'space-between', textAlign: 'left' }}
            >
              <span style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <IconBarras stroke="var(--text-muted)" aria-hidden="true" />
                <span style={{ fontWeight: 800, fontSize: 14.5, color: 'var(--text-muted)' }}>Panel técnico (para especialistas)</span>
              </span>
              <span style={{ fontSize: 13, fontWeight: 800, color: 'var(--peach-dark)', display: 'flex', alignItems: 'center', gap: 4 }}>
                {panelAbierto ? 'Ocultar' : 'Mostrar'}
                {panelAbierto ? <IconChevronArriba aria-hidden="true" /> : <IconChevronAbajo aria-hidden="true" />}
              </span>
            </button>

            {panelAbierto && (
              <div style={{ marginTop: 18, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 24 }}>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 800, color: 'var(--text-muted)', marginBottom: 10 }}>Resumen de la sesión</div>
                  <FilaTecnica etiqueta="PD (0-15)" valor={tecnico.PD} />
                  <FilaTecnica etiqueta="Percentil" valor={tecnico.percentil} />
                  <FilaTecnica etiqueta="Tramo de edad" valor={tecnico.tramo_edad} />
                  <FilaTecnica etiqueta="Confianza media" valor={tecnico.confianza_media} />
                  <FilaTecnica etiqueta="Descriptor" valor={tecnico.descriptor_verbal} />
                </div>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 800, color: 'var(--text-muted)', marginBottom: 10 }}>Probabilidad por figura</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 180, overflowY: 'auto' }}>
                    {sesion.figuras.map((f) => (
                      <div key={f.figura_id} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5 }}>
                        <span style={{ color: 'var(--text-muted)' }}>{f.figura_id} · {f.nombre}</span>
                        <span>{f.prob}</span>
                      </div>
                    ))}
                  </div>
                  <div style={{ fontSize: 12.5, color: 'var(--text-muted)', lineHeight: 1.8, marginTop: 14 }}>
                    Baremo: {sesion.version_baremo}<br />
                    Modelo: {sesion.modelo_git_hash}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="informe-lateral">
          <div style={{ background: 'var(--yellow-light)', borderRadius: 'var(--radius-lg)', padding: '22px 24px' }}>
            <div style={{ fontSize: 12, fontWeight: 800, color: 'var(--yellow-dark)', textTransform: 'uppercase', letterSpacing: '.03em' }}>Sugerencia</div>
            <div style={{ fontSize: 15, fontWeight: 800, marginTop: 6, lineHeight: 1.4 }}>{SUGERENCIA_POR_ACCION[sesion.accion]}</div>
          </div>

          <div className="card" style={{ padding: '20px 22px', display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ fontSize: 13, fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.03em' }}>Acciones</div>
            <button className="btn-secondary no-print" onClick={() => window.print()}>
              <IconDescargar stroke="var(--peach-dark)" aria-hidden="true" /> Exportar informe
            </button>
            <button className="btn-secondary" onClick={() => setCorrigiendo((v) => !v)} aria-expanded={corrigiendo}>
              <IconLapiz stroke="var(--peach-dark)" aria-hidden="true" /> Corregir un puntaje
            </button>
            <button className="btn-secondary" onClick={() => navigate(`/comparar/${sesion.id}/${sesion.figuras[0].figura_id}`)}>
              <IconComparar stroke="var(--peach-dark)" aria-hidden="true" /> Comparar figuras
            </button>

            {corrigiendo && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 4, borderTop: '1px solid var(--border)', paddingTop: 12 }}>
                {sesion.figuras.map((f) => {
                  const actual = f.puntaje_docente ?? f.puntaje
                  return (
                    <div key={f.figura_id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 13, gap: 8 }}>
                      <span>{f.figura_id} · {f.nombre}</span>
                      <button
                        onClick={() => alternarPuntaje(f.figura_id, actual)}
                        aria-label={`${f.nombre}: marcada como ${actual === 1 ? 'lograda' : 'no lograda'}. Cambiar.`}
                        style={{
                          fontSize: 11, fontWeight: 800, padding: '4px 10px', borderRadius: 99, flexShrink: 0,
                          background: actual === 1 ? 'var(--mint-light)' : 'var(--yellow-light)',
                          color: actual === 1 ? 'var(--mint-dark)' : 'var(--yellow-dark)',
                        }}
                      >
                        {actual === 1 ? 'Lograda' : 'No lograda'}
                      </button>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  )
}

function FilaTecnica({ etiqueta, valor }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12.5, marginBottom: 8 }}>
      <span style={{ color: 'var(--text-muted)' }}>{etiqueta}</span>
      <span style={{ fontWeight: 700 }}>{valor ?? '—'}</span>
    </div>
  )
}
