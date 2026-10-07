import { Route, Routes } from 'react-router-dom'
import NuevaEvaluacion from './pages/NuevaEvaluacion'
import Resultados from './pages/Resultados'
import Informe from './pages/Informe'
import Contraste from './pages/Contraste'
import Historial from './pages/Historial'
import PerfilNino from './pages/PerfilNino'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<NuevaEvaluacion />} />
      <Route path="/resultados/:id" element={<Resultados />} />
      <Route path="/informe/:id" element={<Informe />} />
      <Route path="/comparar/:id/:figuraId" element={<Contraste />} />
      <Route path="/historial" element={<Historial />} />
      <Route path="/ninos/:childId" element={<PerfilNino />} />
    </Routes>
  )
}
