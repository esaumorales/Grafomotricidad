import { Link } from 'react-router-dom'
import { IconFlechaIzq } from './icons'

export default function EvaluacionHeader({ sesion, titulo }) {
  return <header className="report-header evaluation-page-header">
    <Link className="report-back" to="/historial"><IconFlechaIzq aria-hidden="true" />Volver al historial</Link>
    <div className="report-header-row"><div><p className="report-kicker">Evaluación grafomotora</p><h1>{titulo} {sesion.nombre_nino || sesion.child_id}</h1><p className="report-person-meta">{sesion.child_id} · {Math.floor(sesion.edad_meses / 12)} años y {sesion.edad_meses % 12} meses{sesion.fecha_evaluacion && ` · ${sesion.fecha_evaluacion.split('-').reverse().join('/')}`}</p></div></div>
  </header>
}
