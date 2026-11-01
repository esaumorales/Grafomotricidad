import { useEvaluacion } from '../components/EvaluacionShell'
import PerfilNino from './PerfilNino'

export default function SeguimientoEvaluacion() {
  const { sesion } = useEvaluacion()
  return <PerfilNino key={sesion.child_id} childId={sesion.child_id} embedded />
}
