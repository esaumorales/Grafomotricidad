import { useState } from 'react'

export default function Acceso() {
  const [token] = useState(() => new URLSearchParams(window.location.hash.slice(1)).get('token'))
  const [enviando, setEnviando] = useState(false)
  const [usuario, setUsuario] = useState('')
  const [error, setError] = useState('')

  async function entrar(event) {
    event.preventDefault()
    setEnviando(true)
    setError('')
    try {
      const respuesta = await fetch(token ? '/api/acceso' : '/api/acceso/demo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(token ? { token } : { usuario }),
      })
      if (!respuesta.ok) {
        const datos = await respuesta.json()
        setError(typeof datos.detail === 'string' ? datos.detail : 'El acceso no está disponible en este momento.')
        return
      }
      window.location.replace('/')
    } catch {
      setError('No se pudo conectar con Trazo. Inténtalo de nuevo.')
    } finally {
      setEnviando(false)
    }
  }

  return <main className="page" style={{ maxWidth: 480, margin: '3rem auto', padding: '1rem' }}>
    <h1>Entrar a Trazo</h1>
    <form onSubmit={entrar}>
      {!token && <>

        <label htmlFor="usuario-demo">Usuario</label>
        <input id="usuario-demo" value={usuario} onChange={(event) => setUsuario(event.target.value)}
          autoCapitalize="none" autoCorrect="off" required placeholder="profesora01" />
      </>}
      <button className="btn btn-primary" disabled={enviando}>{enviando ? 'Entrando…' : 'Entrar'}</button>
    </form>
    {!token && <p><a href="/api/acceso/admin">Acceso de administración</a></p>}
    {error && <p role="alert">{error}</p>}
  </main>
}
