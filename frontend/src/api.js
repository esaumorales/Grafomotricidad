const BASE = '/api'

async function json(res) {
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || JSON.stringify(body)
    } catch {
      // sin cuerpo JSON, se queda con statusText
    }
    throw new Error(`${res.status}: ${detail}`)
  }
  return res.json()
}

export function salud() {
  return fetch(`${BASE}/salud`).then(json)
}

export function evaluar(formData) {
  return fetch(`${BASE}/evaluar`, { method: 'POST', body: formData }).then(json)
}

export function listarSesiones() {
  return fetch(`${BASE}/sesiones`).then(json)
}

export function sesionesDeNino(childId) {
  return fetch(`${BASE}/ninos/${encodeURIComponent(childId)}/sesiones`).then(json)
}

export function obtenerSesion(id) {
  return fetch(`${BASE}/sesiones/${id}`).then(json)
}

export function corregirFigura(sesionId, figuraId, puntajeDocente) {
  return fetch(`${BASE}/sesiones/${sesionId}/figuras/${figuraId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ puntaje_docente: puntajeDocente }),
  }).then(json)
}

export function urlImagenNino(childId, figuraId) {
  return `${BASE}/imagenes/${encodeURIComponent(childId)}/${encodeURIComponent(figuraId)}`
}

export function urlPlantilla(figuraId) {
  return `${BASE}/plantillas/${encodeURIComponent(figuraId)}`
}
