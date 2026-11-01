import { Route, Routes, useLocation } from 'react-router-dom'
import NuevaEvaluacion from './pages/NuevaEvaluacion'
import Resultados from './pages/Resultados'
import Informe from './pages/Informe'
import Contraste from './pages/Contraste'
import Historial from './pages/Historial'
import PerfilNino from './pages/PerfilNino'
import SeguimientoEvaluacion from './pages/SeguimientoEvaluacion'
import EvaluacionShell from './components/EvaluacionShell'

export default function App() {
  const location = useLocation()
  return (
    <Routes>
      <Route path="/" element={<NuevaEvaluacion key={location.search} />} />
      <Route element={<EvaluacionShell />}>
        <Route path="/resultados/:id" element={<Resultados />} />
        <Route path="/informe/:id" element={<Informe />} />
        <Route path="/seguimiento/:id" element={<SeguimientoEvaluacion />} />
      </Route>
      <Route path="/comparar/:id/:figuraId" element={<Contraste />} />
      <Route path="/historial" element={<Historial />} />
      <Route path="/ninos/:childId" element={<PerfilNino />} />
    </Routes>
  )
}
