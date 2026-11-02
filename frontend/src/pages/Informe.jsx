import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useEvaluacion } from '../components/EvaluacionShell'
import InformeMarkdown from '../components/InformeMarkdown'
import ComparacionIA from '../components/ComparacionIA'
import { IconBarras, IconChevronAbajo, IconChevronArriba, IconComparar, IconDescargar, IconLapiz } from '../components/icons'
import { corregirFigura, urlImagenNino } from '../api'

const SUGERENCIA_POR_ACCION = {
  ninguna: 'No hace falta ninguna acción específica por ahora.',
  reforzar_y_revaluar: 'Reforzar en el aula y volver a evaluar en 4 a 6 semanas.',
  derivar: 'Conversar con la familia y considerar derivar a un especialista.',
}

export default function Informe() {
  const navigate = useNavigate()
  const { sesion, setSesion } = useEvaluacion()
  const [panelAbierto, setPanelAbierto] = useState(false)
  const [corrigiendo, setCorrigiendo] = useState(false)
  const [exportando, setExportando] = useState(false)
  const [errorExportacion, setErrorExportacion] = useState(null)

  async function alternarPuntaje(figuraId, actual) {
    const nuevo = actual === 1 ? 0 : 1
    const res = await corregirFigura(sesion.id, figuraId, nuevo)
    setSesion(res)
  }

  async function exportarPdf() {
    setExportando(true)
    setErrorExportacion(null)
    try {
      const { descargarInformePdf } = await import('../informePdf')
      descargarInformePdf(sesion)
    } catch {
      setErrorExportacion('No se pudo generar el PDF. Intenta de nuevo.')
    } finally {
      setExportando(false)
    }
  }

  const tecnico = sesion.panel_tecnico.resumen
  const pendientes = sesion.figuras.filter((f) => f.decision === 'revisar' && f.puntaje_docente == null)

  return (
    <>
      <ComparacionIA sesion={sesion} />

      <div className="report-page">
      {pendientes.length > 0 && <section className="report-review" aria-labelledby="report-review-title">
        <div className="report-review-top"><div><h2 id="report-review-title">{pendientes.length} figuras por revisar</h2><p>El resultado es provisional hasta confirmar sus puntajes.</p></div><button type="button" onClick={() => navigate(`/comparar/${sesion.id}/${pendientes[0].figura_id}`)}>Revisar figuras <IconComparar width={16} height={16} aria-hidden="true" /></button></div>
        <div className="report-review-links">{pendientes.map((f) => <Link key={f.figura_id} className="report-pending-thumb" to={`/comparar/${sesion.id}/${f.figura_id}`} aria-label={`Revisar ${f.nombre}`} title={`Revisar ${f.nombre}`}><span className="pending-figure-number" aria-hidden="true">{Number(f.figura_id.slice(1))}</span><img src={urlImagenNino(sesion.child_id, f.figura_id)} alt={`Dibujo: ${f.nombre}`} loading="lazy" /></Link>)}</div>
        {sesion.aviso_confianza && <details className="report-original-warning"><summary>Ver aviso completo del sistema</summary><p>{sesion.aviso_confianza}</p></details>}
      </section>}
      <div className="informe-layout">
        <div className="informe-principal">
          <div className="card report-body" style={{ padding: '30px 34px' }}>
            <div className="report-outcome"><div><span className="report-eyebrow">Resultado{pendientes.length ? ' provisional' : ''}</span><h2>{tecnico.nivel}</h2></div><div className="report-metrics"><span><strong>{tecnico.PD}<small> / 15</small></strong>puntos</span>{tecnico.percentil != null && <span><strong>{tecnico.percentil}</strong>percentil</span>}</div></div>
            <InformeMarkdown markdown={sesion.informe_docente_md} compact separateWarning={pendientes.length > 0} />
          </div>

          <div className="technical-panel" style={{ background: 'var(--tech-bg)', border: '1.5px solid var(--tech-border)', borderRadius: 'var(--radius-lg)', padding: '22px 30px' }}>
            <button
              onClick={() => setPanelAbierto((v) => !v)}
              aria-expanded={panelAbierto}
              className="technical-toggle" style={{ display: 'flex', width: '100%', alignItems: 'center', justifyContent: 'space-between', textAlign: 'left' }}
            >
              <span style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <IconBarras stroke="var(--text-muted)" aria-hidden="true" />
                <span style={{ fontWeight: 800, fontSize: 16, color: 'var(--text-muted)' }}>Detalles técnicos</span>
              </span>
              <span style={{ fontSize: 14, fontWeight: 800, color: 'var(--peach-dark)', display: 'flex', alignItems: 'center', gap: 4 }}>
                {panelAbierto ? 'Ocultar' : 'Mostrar'}
                {panelAbierto ? <IconChevronArriba aria-hidden="true" /> : <IconChevronAbajo aria-hidden="true" />}
              </span>
            </button>

            {panelAbierto && (
              <div className="technical-grid" style={{ marginTop: 18, display: 'grid', gap: 24 }}>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 800, color: 'var(--text-muted)', marginBottom: 10 }}>Resumen de la sesión</div>
                  <FilaTecnica etiqueta="PD (0-15)" valor={tecnico.PD} />
                  <FilaTecnica etiqueta="Percentil" valor={tecnico.percentil} />
                  <FilaTecnica etiqueta="Tramo de edad" valor={tecnico.tramo_edad} />
                  <FilaTecnica etiqueta="Confianza media" valor={tecnico.confianza_media} />
                  <FilaTecnica etiqueta="Descriptor" valor={tecnico.descriptor_verbal} />
                </div>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 800, color: 'var(--text-muted)', marginBottom: 10 }}>Probabilidad por figura</div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 180, overflowY: 'auto' }}>
                    {sesion.figuras.map((f) => (
                      <div key={f.figura_id} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14 }}>
                        <span style={{ color: 'var(--text-muted)' }}>{f.figura_id} · {f.nombre}</span>
                        <span>{f.prob}</span>
                      </div>
                    ))}
                  </div>
                  <div style={{ fontSize: 14, color: 'var(--text-muted)', lineHeight: 1.8, marginTop: 14 }}>
                    Baremo: {sesion.version_baremo}<br />
                    Modelo: {sesion.modelo_git_hash}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="informe-lateral">
          <div className="report-next-step" style={{ background: 'var(--yellow-light)', borderRadius: 'var(--radius-lg)', padding: '22px 24px' }}>
            <div style={{ fontSize: 14, fontWeight: 800, color: 'var(--yellow-dark)', textTransform: 'uppercase', letterSpacing: '.03em' }}>{pendientes.length ? 'Siguiente paso' : 'Sugerencia'}</div>
            <div style={{ fontSize: 16, fontWeight: 800, marginTop: 6, lineHeight: 1.4 }}>{pendientes.length ? 'Revisa las figuras pendientes y confirma sus puntajes.' : SUGERENCIA_POR_ACCION[sesion.accion]}</div>
          </div>

          <div className="card report-action-panel" style={{ padding: '20px 22px', display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ fontSize: 14, fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.03em' }}>Revisión y descarga</div>
            <button className="btn-secondary" onClick={() => setCorrigiendo((v) => !v)} aria-expanded={corrigiendo}>
              <IconLapiz stroke="var(--peach-dark)" aria-hidden="true" /> Corregir un puntaje
            </button>
            <button className="btn-secondary" onClick={() => navigate(`/comparar/${sesion.id}/${sesion.figuras[0].figura_id}`)}>
              <IconComparar stroke="var(--peach-dark)" aria-hidden="true" /> Comparar figuras
            </button>

            <div className="report-download">
              <button type="button" className="btn-secondary no-print" onClick={exportarPdf} disabled={exportando}><IconDescargar aria-hidden="true" />{exportando ? 'Generando PDF…' : 'Descargar informe PDF'}</button>
              <span>Documento listo para guardar o compartir.</span>
              {errorExportacion && <p role="alert">{errorExportacion}</p>}
            </div>

            {corrigiendo && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 4, borderTop: '1px solid var(--border)', paddingTop: 12 }}>
                {sesion.figuras.map((f) => {
                  const actual = f.puntaje_docente ?? f.puntaje
                  return (
                    <div key={f.figura_id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 14, gap: 8 }}>
                      <span>{f.figura_id} · {f.nombre}</span>
                      <button
                        onClick={() => alternarPuntaje(f.figura_id, actual)}
                        aria-label={`${f.nombre}: marcada como ${actual === 1 ? 'lograda' : 'no lograda'}. Cambiar.`}
                        style={{
                          fontSize: 14, fontWeight: 800, padding: '4px 10px', borderRadius: 99, flexShrink: 0,
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
      </div>
    </>
  )
}

function FilaTecnica({ etiqueta, valor }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14, marginBottom: 8 }}>
      <span style={{ color: 'var(--text-muted)' }}>{etiqueta}</span>
      <span style={{ fontWeight: 700 }}>{valor ?? '—'}</span>
    </div>
  )
}
