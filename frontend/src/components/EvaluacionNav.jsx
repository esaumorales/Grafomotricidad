import { Link } from 'react-router-dom'
import { IconBarras, IconComparar, IconReloj } from './icons'

export default function EvaluacionNav({ sesion, activa }) {
  return <nav className="evaluation-navigation" aria-label="Vistas de la evaluación">
    <Link to={`/resultados/${sesion.id}`} aria-current={activa === 'resultados' ? 'page' : undefined}><IconBarras width={17} height={17} aria-hidden="true" />Resultados</Link>
    <Link to={`/informe/${sesion.id}`} aria-current={activa === 'informe' ? 'page' : undefined}><IconComparar width={17} height={17} aria-hidden="true" />Informe</Link>
    <Link to={`/seguimiento/${sesion.id}`} aria-current={activa === 'seguimiento' ? 'page' : undefined}><IconReloj width={17} height={17} aria-hidden="true" />Seguimiento</Link>
  </nav>
}
