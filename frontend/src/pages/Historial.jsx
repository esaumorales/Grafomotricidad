import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import Layout from '../components/Layout'
import { Cargando, ErrorConReintento } from '../components/Estado'
import { IconBuscar, IconFlechaDer, IconMas, IconReloj } from '../components/icons'
import { listarSesiones } from '../api'

function iniciales(nombre) {
  return nombre.split(' ').filter(Boolean).slice(0, 2).map((p) => p[0].toUpperCase()).join('')
}

function fechaCorta(iso) {
  return new Date(iso).toLocaleDateString('es-PE', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'America/Lima' })
}

export default function Historial() {
  const [sesiones, setSesiones] = useState(null)
  const [error, setError] = useState(null)
  const [busqueda, setBusqueda] = useState('')
  const [orden, setOrden] = useState('recientes')

  const cargar = useCallback(() => {
    setError(null)
    listarSesiones().then(setSesiones).catch((e) => setError(e.message))
  }, [])

  useEffect(cargar, [cargar])

  const filtradas = useMemo(() => {
    if (!sesiones) return []
    const q = busqueda.trim().toLowerCase()
    const resultado = sesiones.filter(
      (s) => !q || s.child_id.toLowerCase().includes(q) || (s.nombre_nino || '').toLowerCase().includes(q)
    )
    return [...resultado].sort((a, b) => orden === 'recientes' ? b.fecha.localeCompare(a.fecha) : a.fecha.localeCompare(b.fecha))
  }, [sesiones, busqueda, orden])

  return (
    <Layout>
      <div className="history-page">
        <header className="history-header"><div><h1>Historial de evaluaciones</h1><p>Busca una evaluación para consultar sus resultados, informe y seguimiento.</p></div><Link className="history-new" to="/"><IconMas width={17} height={17} aria-hidden="true" />Nueva evaluación</Link></header>
        <section className="history-records" aria-label="Evaluaciones guardadas">
          <div className="history-toolbar">
            <div className="history-search"><IconBuscar width={17} height={17} aria-hidden="true" /><label htmlFor="busqueda-historial" className="visually-hidden">Buscar por nombre o código</label><input id="busqueda-historial" type="search" placeholder="Buscar por nombre o código" value={busqueda} onChange={(e) => setBusqueda(e.target.value)} /></div>
            <div className="history-sort"><label htmlFor="history-order">Ordenar</label><select id="history-order" value={orden} onChange={(e) => setOrden(e.target.value)}><option value="recientes">Más recientes primero</option><option value="antiguas">Más antiguas primero</option></select></div>
          </div>
          {error && <div className="history-feedback"><ErrorConReintento mensaje={error} onReintentar={cargar} /></div>}
          {!error && !sesiones && <div className="history-feedback"><Cargando filas={3} /></div>}
          {!error && sesiones && sesiones.length === 0 && <div className="history-empty"><IconReloj width={28} height={28} aria-hidden="true" /><h2>Aún no hay evaluaciones</h2><p>Las evaluaciones que completes aparecerán aquí.</p><Link to="/">Crear la primera evaluación <IconFlechaDer width={15} height={15} aria-hidden="true" /></Link></div>}
          {!error && sesiones && sesiones.length > 0 && <>
            <div className="history-count" role="status">{filtradas.length} {filtradas.length === 1 ? 'evaluación' : 'evaluaciones'}{busqueda.trim() && ` de ${sesiones.length}`}</div>
            {filtradas.length ? <table className="history-table"><thead><tr><th scope="col">Niño o niña</th><th scope="col">Edad al evaluar</th><th scope="col">Fecha de registro</th><th scope="col">Nivel</th><th scope="col"><span className="visually-hidden">Acciones</span></th></tr></thead><tbody>
              {filtradas.map((s) => {
                const nombre = s.nombre_nino || s.child_id
                const estado = s.accion === 'ninguna' ? 'adequate' : s.accion === 'derivar' ? 'support' : 'review'
                return <tr key={s.id}>
                  <td className="history-person-cell"><div className="history-person"><span className="history-avatar" aria-hidden="true">{iniciales(nombre)}</span><div><span className="history-name">{nombre}</span><span className="history-code">Código: {s.child_id}</span></div></div></td>
                  <td data-label="Edad al evaluar">{Math.floor(s.edad_meses / 12)} años {s.edad_meses % 12} meses</td>
                  <td data-label="Registro">{fechaCorta(s.fecha)}</td>
                  <td data-label="Nivel"><span className={`history-level ${estado}`}><span aria-hidden="true" />{s.nivel}</span></td>
                  <td className="history-actions"><div className="history-action-buttons"><Link className="history-open" to={`/informe/${s.id}`} aria-label={`Ver informe de ${nombre}, evaluación ${s.id}`}>Ver informe<IconFlechaDer width={15} height={15} aria-hidden="true" /></Link></div></td>
                </tr>
              })}
            </tbody></table> : <div className="history-empty"><IconBuscar width={26} height={26} aria-hidden="true" /><h2>No hay coincidencias</h2><p>Prueba con otro nombre o código.</p><button type="button" onClick={() => setBusqueda('')}>Limpiar búsqueda</button></div>}
          </>}
        </section>
      </div>
    </Layout>
  )
}
