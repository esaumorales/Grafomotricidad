import { useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../components/Layout'
import { IconCheck, IconSubir } from '../components/icons'
import { FIGURAS } from '../figuras'
import { evaluar } from '../api'

/**
 * Intenta leer el número de figura SOLO cuando el nombre del archivo lo dice de forma
 * inequívoca (F07.jpg, figura_7.png, fig-07.jpeg, o el archivo es solo el número: 7.jpg).
 * Las fotos reales de un celular (IMG_2026...jpg, 20260911_142033.jpg) tienen números
 * largos que no significan nada -> a propósito NO se intenta adivinar ahí, para no
 * mandar una foto cualquiera a una figura al azar. Esos casos se llenan en el orden
 * en que se soltaron/eligieron (ver asignarArchivos).
 */
function figuraDesdeNombre(nombre) {
  const base = nombre.replace(/\.[^.]+$/, '').trim()
  const patrones = [
    /^f\W*0*(\d{1,2})$/i,
    /^fig(?:ura)?\W*0*(\d{1,2})$/i,
    /^0*(\d{1,2})$/,
  ]
  for (const pat of patrones) {
    const m = base.match(pat)
    if (m) {
      const n = parseInt(m[1], 10)
      if (n >= 1 && n <= 15) return `F${String(n).padStart(2, '0')}`
    }
  }
  return null
}

export default function NuevaEvaluacion() {
  const navigate = useNavigate()
  const [childId, setChildId] = useState('')
  const [nombreNino, setNombreNino] = useState('')
  const [anios, setAnios] = useState(4)
  const [meses, setMeses] = useState(0)
  const [mano, setMano] = useState('D')
  const [archivos, setArchivos] = useState({}) // { F01: File, ... }
  const [enviando, setEnviando] = useState(false)
  const [error, setError] = useState(null)
  const inputMasivoRef = useRef(null)
  const inputIndividualRef = useRef({})

  const subidas = Object.keys(archivos).length
  const previews = useMemo(() => {
    const out = {}
    for (const [fid, file] of Object.entries(archivos)) out[fid] = URL.createObjectURL(file)
    return out
  }, [archivos])

  function asignarArchivos(fileList) {
    setArchivos((prev) => {
      const next = { ...prev }
      const ocupados = new Set(Object.keys(next))
      const sinFigura = []
      for (const file of fileList) {
        const fid = figuraDesdeNombre(file.name)
        if (fid && !ocupados.has(fid)) {
          next[fid] = file
          ocupados.add(fid)
        } else {
          sinFigura.push(file)
        }
      }
      const libres = FIGURAS.map((f) => f.id).filter((id) => !ocupados.has(id))
      sinFigura.forEach((file, i) => {
        if (libres[i]) {
          next[libres[i]] = file
          ocupados.add(libres[i])
        }
      })
      return next
    })
  }

  function onDrop(e) {
    e.preventDefault()
    asignarArchivos(Array.from(e.dataTransfer.files))
  }

  function onElegirMasivo(e) {
    asignarArchivos(Array.from(e.target.files))
    e.target.value = ''
  }

  function onElegirIndividual(fid, e) {
    const file = e.target.files[0]
    if (file) setArchivos((prev) => ({ ...prev, [fid]: file }))
    e.target.value = ''
  }

  const edadMeses = anios * 12 + meses
  const listoParaEnviar = childId.trim() && subidas === 15 && !enviando

  async function onSubmit(e) {
    e.preventDefault()
    if (!listoParaEnviar) return
    setEnviando(true)
    setError(null)
    try {
      const fd = new FormData()
      fd.append('child_id', childId.trim())
      fd.append('edad_meses', String(edadMeses))
      fd.append('nombre_nino', nombreNino.trim())
      fd.append('figura_ids', FIGURAS.map((f) => f.id).join(','))
      for (const f of FIGURAS) fd.append('fotos', archivos[f.id])
      const res = await evaluar(fd)
      navigate(`/resultados/${res.id}`)
    } catch (err) {
      setError(err.message || 'No se pudo evaluar la sesión.')
      setEnviando(false)
    }
  }

  return (
    <Layout>
      <div>
        <h1 style={{ fontSize: 32 }}>Nueva evaluación</h1>
        <p style={{ margin: '6px 0 0', color: 'var(--text-muted)', fontSize: 15 }}>
          Completa los datos del niño o la niña y sube las 15 fotos de las figuras que copió.
        </p>
      </div>

      <form onSubmit={onSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
        <div className="card">
          <h2 style={{ fontSize: 18, marginBottom: 20 }}>Datos del niño o la niña</h2>
          <div className="form-grid">
            <Campo id="campo-child-id" label="Código del niño/a">
              <input
                id="campo-child-id"
                required
                value={childId}
                onChange={(e) => setChildId(e.target.value)}
                placeholder="NINO_0034"
                style={inputStyle}
              />
            </Campo>

            <fieldset style={fieldsetStyle}>
              <legend style={legendStyle}>Edad</legend>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                <label htmlFor="campo-anios" className="visually-hidden">Años</label>
                <input id="campo-anios" type="number" min={3} max={5} value={anios}
                  onChange={(e) => setAnios(Number(e.target.value))} style={{ ...inputStyle, width: 64 }} />
                <span style={{ color: 'var(--text-muted)', fontSize: 13, fontWeight: 700 }}>años</span>
                <label htmlFor="campo-meses" className="visually-hidden">Meses</label>
                <input id="campo-meses" type="number" min={0} max={11} value={meses}
                  onChange={(e) => setMeses(Number(e.target.value))} style={{ ...inputStyle, width: 64 }} />
                <span style={{ color: 'var(--text-muted)', fontSize: 13, fontWeight: 700 }}>meses</span>
              </div>
            </fieldset>

            <fieldset style={fieldsetStyle}>
              <legend style={legendStyle}>Mano usada</legend>
              <div style={{ display: 'flex', gap: 8 }}>
                {['D', 'I'].map((v) => (
                  <button
                    type="button"
                    key={v}
                    onClick={() => setMano(v)}
                    aria-pressed={mano === v}
                    style={{
                      flex: 1, textAlign: 'center', padding: '11px 0', borderRadius: 'var(--radius-sm)',
                      fontWeight: mano === v ? 800 : 700,
                      background: mano === v ? 'var(--peach)' : 'var(--bg)',
                      color: mano === v ? 'var(--text)' : 'var(--text-muted)',
                      border: mano === v ? 'none' : '2px solid var(--border)',
                    }}
                  >
                    {v === 'D' ? 'Derecha' : 'Izquierda'}
                  </button>
                ))}
              </div>
            </fieldset>

            <div style={{ gridColumn: '1 / -1' }}>
              <Campo id="campo-nombre" label="Nombre (opcional, solo para tu referencia)">
                <input id="campo-nombre" value={nombreNino} onChange={(e) => setNombreNino(e.target.value)}
                  placeholder="Valentina" style={{ ...inputStyle, maxWidth: 340 }} />
              </Campo>
            </div>
          </div>
        </div>

        <div className="card" style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8, flexWrap: 'wrap', gap: 8 }}>
            <h2 style={{ fontSize: 18 }}>Fotos de las 15 figuras</h2>
            <div style={{ fontSize: 13, fontWeight: 800, color: 'var(--mint-dark)' }} aria-live="polite">
              {subidas} de 15 fotos subidas
            </div>
          </div>
          <div
            role="progressbar" aria-valuenow={subidas} aria-valuemin={0} aria-valuemax={15}
            aria-label="Fotos subidas"
            style={{ height: 8, borderRadius: 99, background: 'var(--border)', overflow: 'hidden', marginBottom: 22 }}
          >
            <div style={{ width: `${(subidas / 15) * 100}%`, height: '100%', background: 'var(--mint-icon)', borderRadius: 99, transition: 'width .2s' }} />
          </div>

          <div
            onDrop={onDrop}
            onDragOver={(e) => e.preventDefault()}
            style={{
              borderRadius: 'var(--radius-lg)', border: '3px dashed var(--peach)', background: 'var(--peach-light)',
              padding: '28px 32px', display: 'flex', alignItems: 'center', gap: 22, marginBottom: 26, flexWrap: 'wrap',
            }}
          >
            <div aria-hidden="true" style={{ width: 56, height: 56, borderRadius: '50%', background: 'var(--peach-icon)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <IconSubir stroke="white" />
            </div>
            <div style={{ flex: 1, minWidth: 200 }}>
              <div style={{ fontWeight: 800, fontSize: 16.5 }}>Arrastra aquí las 15 fotos, todas a la vez</div>
              <div style={{ fontSize: 13.5, color: 'var(--text-muted)', marginTop: 3, fontWeight: 600 }}>
                O haz clic para elegirlas juntas desde tu galería. No importa el orden en que las sueltes:
                las acomodamos solas por figura y puedes corregir cualquiera abajo.
              </div>
            </div>
            <label htmlFor="input-masivo" className="visually-hidden">Elegir las 15 fotos a la vez</label>
            <input id="input-masivo" ref={inputMasivoRef} type="file" accept="image/*" multiple hidden onChange={onElegirMasivo} />
            <button type="button" className="btn-primary" style={{ background: 'var(--peach)', boxShadow: 'none', padding: '13px 26px', fontSize: 14.5 }}
              onClick={() => inputMasivoRef.current.click()}>
              Elegir fotos
            </button>
          </div>

          <div style={{ fontSize: 12, fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.03em', marginBottom: 12 }}>
            Revisa que cada foto quedó en su figura
          </div>

          <div className="figuras-grid">
            {FIGURAS.map((f) => {
              const tiene = Boolean(archivos[f.id])
              return (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => inputIndividualRef.current[f.id]?.click()}
                  aria-label={tiene ? `Figura ${f.numero}, ${f.nombre}: foto cargada. Cambiar foto.` : `Figura ${f.numero}, ${f.nombre}: pendiente. Subir foto.`}
                  style={{
                    width: '100%', borderRadius: 'var(--radius-md)', padding: 14, position: 'relative',
                    textAlign: tiene ? 'left' : 'center',
                    border: tiene ? '2px solid var(--mint-light)' : '2.5px dashed var(--border)',
                    background: tiene ? 'var(--mint-light)' : 'transparent',
                    display: 'flex', flexDirection: 'column',
                    alignItems: tiene ? 'flex-start' : 'center',
                    justifyContent: 'center', gap: 8, minHeight: 128,
                  }}
                >
                  <input
                    ref={(el) => { inputIndividualRef.current[f.id] = el }}
                    type="file" accept="image/*" hidden onChange={(e) => onElegirIndividual(f.id, e)}
                    aria-label={`Foto de la figura ${f.numero}, ${f.nombre}`}
                  />
                  {tiene ? (
                    <>
                      <div aria-hidden="true" style={{ position: 'absolute', top: 10, right: 10, width: 22, height: 22, borderRadius: '50%', background: 'var(--mint-icon)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                        <IconCheck width={13} height={13} strokeWidth={3} stroke="white" />
                      </div>
                      <img src={previews[f.id]} alt="" style={{ width: 40, height: 40, objectFit: 'cover', borderRadius: 8 }} />
                      <div style={{ fontSize: 11, fontWeight: 800, color: 'var(--text-muted)', marginTop: 10 }}>Figura {f.numero}</div>
                      <div style={{ fontSize: 12.5, fontWeight: 700 }}>{f.nombre}</div>
                    </>
                  ) : (
                    <>
                      <svg aria-hidden="true" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                        <circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" />
                      </svg>
                      <div style={{ fontSize: 11, fontWeight: 800, color: 'var(--text-muted)' }}>Figura {f.numero} · {f.nombre}</div>
                      <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)' }}>Pendiente</div>
                    </>
                  )}
                </button>
              )
            })}
          </div>

          {error && (
            <div role="alert" style={{ marginTop: 20, color: 'var(--yellow-dark)', fontWeight: 700, fontSize: 14 }}>{error}</div>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 28 }}>
            <button type="submit" className="btn-primary" disabled={!listoParaEnviar}>
              {enviando ? 'Evaluando…' : 'Evaluar ahora'}
              {!enviando && (
                <svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--text)" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 12h14M13 6l6 6-6 6" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </form>
    </Layout>
  )
}

const inputStyle = {
  padding: '12px 14px', border: '2px solid var(--border)', borderRadius: 'var(--radius-sm)',
  fontSize: 14, color: 'var(--text)', background: 'var(--bg)', width: '100%',
}

const fieldsetStyle = { border: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 6 }
const legendStyle = {
  fontSize: 12, fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase',
  letterSpacing: '.03em', padding: 0, marginBottom: 2,
}

function Campo({ id, label, children }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <label htmlFor={id} style={{ fontSize: 12, fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '.03em' }}>
        {label}
      </label>
      {children}
    </div>
  )
}
