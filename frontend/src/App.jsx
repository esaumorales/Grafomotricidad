import { useEffect, useState } from 'react'
import Acceso from './pages/Acceso'
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
  const [acceso, setAcceso] = useState(null)
  useEffect(() => {
    if (location.pathname === '/acceso') return
    const controller = new AbortController()
    fetch('/api/cuenta', { signal: controller.signal, cache: 'no-store' })
      .then((res) => setAcceso(res.status === 401 ? 'requerido' : 'listo'))
      .catch(() => {})
    return () => controller.abort()
  }, [location.pathname])

  if (acceso === 'requerido' && location.pathname !== '/acceso') return <Acceso />
  return (
    <Routes>
      <Route path="/acceso" element={<Acceso />} />
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
