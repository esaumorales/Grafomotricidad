import { useEffect, useId, useState } from 'react'
import { Outlet, useMatch, useOutletContext } from 'react-router-dom'
import Layout from './Layout'
import EvaluacionHeader from './EvaluacionHeader'
import EvaluacionNav from './EvaluacionNav'
import { Cargando, ErrorConReintento } from './Estado'
import { obtenerSesion } from '../api'

export const useEvaluacion = () => useOutletContext()

export default function EvaluacionShell() {
  const match = useMatch('/:vista/:id')
  const id = match?.params.id
  const vista = match?.params.vista
  const shellId = useId()
  const [estado, setEstado] = useState({id:null,sesion:null,error:null})
  const [intento,setIntento] = useState(0)
  useEffect(() => {
    let activo = true
    obtenerSesion(id).then((sesion) => { if(activo) setEstado({id,sesion,error:null}) })
      .catch((error) => { if(activo) setEstado({id,sesion:null,error:error.message}) })
    return () => { activo = false }
  }, [id,intento])
  const sesion = estado.id === id ? estado.sesion : null
  const error = estado.id === id ? estado.error : null
  const setSesion = (actualizada) => setEstado({id,sesion:actualizada,error:null})
  return <Layout>
    {error ? <ErrorConReintento mensaje={error} onReintentar={() => setIntento((v) => v+1)} /> : !sesion ? <Cargando /> : <>
      <EvaluacionHeader sesion={sesion} titulo="Evaluación de" />
      <EvaluacionNav sesion={sesion} activa={vista} />
      <div className="evaluation-view-content" data-shell-id={shellId}><Outlet context={{sesion,setSesion}} /></div>
    </>}
  </Layout>
}
