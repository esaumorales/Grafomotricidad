import { useEffect, useRef, useState } from 'react'

function detectar(ctx, w, h) {
  const { data } = ctx.getImageData(0, 0, w, h)
  const gray = new Uint8Array(w * h)
  const hist = new Uint32Array(256)
  for (let i = 0; i < gray.length; i++) {
    const j = i * 4
    hist[gray[i] = (data[j] * 77 + data[j + 1] * 150 + data[j + 2] * 29) >> 8]++
  }
  function percentil(p) {
    let n = 0
    return hist.findIndex((v) => (n += v) >= gray.length * p)
  }
  const oscuro = percentil(0.15)
  const claro = percentil(0.85)
  if (claro < 65) return null
  for (const fraccion of [0.3, 0.5, 0.18]) {
    const esquinas = buscarBordes(gray, w, h, oscuro + (claro - oscuro) * fraccion)
    if (esquinas && pareceHoja(esquinas, w, h)) return esquinas
  }
  const horizontal = bordesPorFranja(gray, w, h, false)
  const vertical = bordesPorFranja(gray, h, w, true)
  if (!horizontal || !vertical) return null
  const [izq, der] = horizontal
  const [arriba, abajo] = vertical
  const interseccion = ([a, b], [c, d]) => {
    const x = (a + b * c) / (1 - b * d)
    return [x / w, (c + d * x) / h]
  }
  const puntos = [interseccion(izq, arriba), interseccion(der, arriba), interseccion(der, abajo), interseccion(izq, abajo)]
  return pareceHoja(puntos, w, h) ? puntos : null
}

function pareceHoja(puntos, w, h) {
  if (!puntos.every((p) => p.every((v) => v > 0.035 && v < 0.965))) return false
  const lados = puntos.map(([x, y], i) => {
    const [nx, ny] = puntos[(i + 1) % 4]
    return Math.hypot((x - nx) * w, (y - ny) * h)
  })
  const ancho = (lados[0] + lados[2]) / 2
  const alto = (lados[1] + lados[3]) / 2
  return ancho / alto >= 0.53 && ancho / alto <= 0.88 &&
    ancho * alto >= w * h * 0.25 &&
    Math.min(lados[0], lados[2]) / Math.max(lados[0], lados[2]) >= 0.72 &&
    Math.min(lados[1], lados[3]) / Math.max(lados[1], lados[3]) >= 0.72
}
function bordesPorFranja(gray, ancho, alto, transpuesta) {
  const leer = (x, y) => gray[transpuesta ? x * alto + y : y * ancho + x]
  const rectas = [0, 1].map((lado) => {
    const signo = lado === 0 ? 1 : -1
    const muestras = []
    for (let y = Math.round(alto * 0.24); y < alto * 0.76; y += 3) {
      const fila = []
      for (let paso = 6; paso < ancho * 0.36; paso++) {
        const x = lado === 0 ? paso : ancho - 1 - paso
        const fuerza = leer(x + 3 * signo, y) - leer(x - 3 * signo, y)
        if (fuerza >= 7) fila.push([x, fuerza])
      }
      muestras.push([y, fila])
    }
    let mejor = null
    let mayor = 0
    for (let pendiente = -0.4; pendiente <= 0.401; pendiente += 0.025) {
      const votos = new Float32Array(ancho)
      const filas = new Uint8Array(ancho)
      for (const [y, candidatos] of muestras) {
        const peso = new Float32Array(ancho)
        for (const [x, fuerza] of candidatos) {
          const centro = Math.round(x - pendiente * (y - alto / 2))
          for (let i = Math.max(0, centro - 1); i <= Math.min(ancho - 1, centro + 1); i++) {
            peso[i] = Math.max(peso[i], 1 + Math.min(fuerza, 30) / 60)
          }
        }
        for (let i = 0; i < ancho; i++) {
          votos[i] += peso[i]
          if (peso[i]) filas[i]++
        }
      }
      for (let i = 0; i < ancho; i++) {
        if (filas[i] >= muestras.length * 0.54 && votos[i] > mayor) {
          mayor = votos[i]
          mejor = [i - pendiente * alto / 2, pendiente]
        }
      }
    }
    return mejor
  })
  return rectas.every(Boolean) ? rectas : null
}

function buscarBordes(gray, w, h, umbral) {
  const esquinas = [null, null, null, null]
  let cantidad = 0
  for (let y = 1; y < h - 1; y++) {
    for (let x = 1; x < w - 1; x++) {
      const i = y * w + x
      if (Math.min(gray[i], gray[i - 1], gray[i + 1], gray[i - w], gray[i + w]) < umbral) continue
      cantidad++
      const valores = [x + y, y - x, -x - y, x - y]
      valores.forEach((valor, k) => {
        if (!esquinas[k] || valor < esquinas[k].valor) esquinas[k] = { x, y, valor }
      })
    }
  }
  if (cantidad < w * h * 0.25 || cantidad > w * h * 0.85 ||
      esquinas.some((p) => !p || p.x < 5 || p.y < 5 || p.x > w - 6 || p.y > h - 6)) return null

  const centro = esquinas.reduce((sum, p) => ({ x: sum.x + p.x / 4, y: sum.y + p.y / 4 }), { x: 0, y: 0 })
  const leer = (x, y) => gray[Math.round(y) * w + Math.round(x)]
  const ladosValidos = esquinas.every((a, i) => {
    const b = esquinas[(i + 1) % 4]
    if (Math.hypot(b.x - a.x, b.y - a.y) < Math.min(w, h) * 0.40) return false
    let bordes = 0
    for (let paso = 1; paso < 10; paso++) {
      const x = a.x + (b.x - a.x) * paso / 10
      const y = a.y + (b.y - a.y) * paso / 10
      const dx = (centro.x - x) * 0.055
      const dy = (centro.y - y) * 0.055
      if (leer(x + dx, y + dy) - leer(x - dx, y - dy) >= 7) bordes++
    }
    return bordes >= 6
  })
  return ladosValidos ? esquinas.map(({ x, y }) => [x / w, y / h]) : null
}

function capturar(video, esquinas) {
  const foto = document.createElement('canvas')
  const escala = Math.min(1, 1800 / Math.max(video.videoWidth, video.videoHeight))
  foto.width = Math.round(video.videoWidth * escala)
  foto.height = Math.round(video.videoHeight * escala)
  const ctx = foto.getContext('2d', { willReadFrequently: Boolean(esquinas) })
  ctx.drawImage(video, 0, 0, foto.width, foto.height)
  if (!esquinas) return foto

  const [a, b, c, d] = esquinas.map(([x, y]) => [x * foto.width, y * foto.height])
  const distancia = (p, q) => Math.hypot(p[0] - q[0], p[1] - q[1])
  const salida = document.createElement('canvas')
  salida.width = Math.round(Math.max(distancia(a, b), distancia(d, c)))
  salida.height = Math.round(Math.max(distancia(a, d), distancia(b, c)))
  const destino = salida.getContext('2d')
  const pixels = destino.createImageData(salida.width, salida.height)
  const original = ctx.getImageData(0, 0, foto.width, foto.height).data
  const dx1 = b[0] - c[0], dx2 = d[0] - c[0]
  const dy1 = b[1] - c[1], dy2 = d[1] - c[1]
  const sx = a[0] - b[0] + c[0] - d[0], sy = a[1] - b[1] + c[1] - d[1]
  const det = dx1 * dy2 - dx2 * dy1
  if (Math.abs(det) < 1) return foto
  const g = (sx * dy2 - dx2 * sy) / det
  const h = (dx1 * sy - sx * dy1) / det
  for (let y = 0; y < salida.height; y++) {
    const v = y / salida.height
    for (let x = 0; x < salida.width; x++) {
      const u = x / salida.width
      const z = 1 + g * u + h * v
      const ox = Math.round((a[0] + ((1 + g) * b[0] - a[0]) * u + ((1 + h) * d[0] - a[0]) * v) / z)
      const oy = Math.round((a[1] + ((1 + g) * b[1] - a[1]) * u + ((1 + h) * d[1] - a[1]) * v) / z)
      const src = (oy * foto.width + ox) * 4
      const dst = (y * salida.width + x) * 4
      pixels.data[dst] = original[src]
      pixels.data[dst + 1] = original[src + 1]
      pixels.data[dst + 2] = original[src + 2]
      pixels.data[dst + 3] = 255
    }
  }
  destino.putImageData(pixels, 0, 0)
  return salida
}

export default function EscanerHoja({ numero, onClose, onFile, onNative }) {
  const dialog = useRef(null)
  const video = useRef(null)
  const disparando = useRef(false)
  const [intento, repetir] = useState(0)
  const [foto, setFoto] = useState(null)
  const [vista, setVista] = useState('')
  const [mensaje, setMensaje] = useState('Abriendo la cámara…')
  const [lista, setLista] = useState(false)
  const [marco, setMarco] = useState(null)

  useEffect(() => {
    dialog.current.showModal()
  }, [])

  useEffect(() => {
    if (!foto) return
    const url = URL.createObjectURL(foto)
    setVista(url)
    return () => URL.revokeObjectURL(url)
  }, [foto])

  function tomar(esquinas) {
    if (disparando.current || !video.current?.videoWidth) return
    disparando.current = true
    capturar(video.current, esquinas).toBlob((blob) => {
      if (blob) setFoto(new File([blob], `hoja-${numero}.jpg`, { type: 'image/jpeg' }))
      else {
        disparando.current = false
        setMensaje('No se pudo guardar la foto. Intenta de nuevo.')
      }
    }, 'image/jpeg', 0.94)
  }

  useEffect(() => {
    if (foto) return
    let activo = true
    let stream
    let timer
    let estable = 0
    let anterior
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d', { willReadFrequently: true })

    async function abrir() {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: false, video: { facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1920 } },
        })
        if (!activo) { stream.getTracks().forEach((track) => track.stop()); return }
        video.current.srcObject = stream
        await video.current.play()
        if (!activo) return
        setLista(true)
        timer = setInterval(() => {
          const v = video.current
          if (!v?.videoWidth || disparando.current) return
          canvas.width = Math.round(240 * v.videoWidth / Math.max(v.videoWidth, v.videoHeight))
          canvas.height = Math.round(240 * v.videoHeight / Math.max(v.videoWidth, v.videoHeight))
          ctx.drawImage(v, 0, 0, canvas.width, canvas.height)
          const puntos = detectar(ctx, canvas.width, canvas.height)
          setMarco(puntos)
          if (!puntos) {
            estable = 0
            anterior = null
            setMensaje('Deja un margen alrededor de toda la hoja.')
            return
          }
          const quieta = anterior && puntos.every(([x, y], i) => Math.hypot(x - anterior[i][0], y - anterior[i][1]) < 0.015)
          if (!quieta) { estable = Date.now(); anterior = puntos }
          setMensaje('Hoja detectada. Mantén el celular quieto.')
          if (quieta && Date.now() - estable >= 1200) tomar(puntos)
        }, 170)
      } catch {
        if (activo) setMensaje('No se pudo abrir la cámara. Revisa el permiso o usa la cámara del dispositivo.')
      }
    }

    abrir()
    return () => {
      activo = false
      clearInterval(timer)
      stream?.getTracks().forEach((track) => track.stop())
    }
  }, [foto, intento])

  function nuevaToma() {
    disparando.current = false
    setLista(false)
    setMarco(null)
    setVista('')
    setFoto(null)
    setMensaje('Abriendo la cámara…')
    repetir((n) => n + 1)
  }

  return (
    <dialog ref={dialog} className="scanner-dialog" onCancel={onClose} aria-labelledby="scanner-title">
      <header className="scanner-header">
        <h2 id="scanner-title">{foto ? `Revisar foto ${numero}` : `Escanear hoja ${numero}`}</h2>
        <button type="button" className="scanner-close" aria-label="Cerrar escáner" onClick={onClose}>×</button>
      </header>
      <p className="scanner-status" role="status">{foto ? 'Comprueba que se vean todas las figuras y los trazos.' : mensaje}</p>
      {foto ? <img className="scanner-preview" src={vista || undefined} alt="Vista previa de la hoja" /> :
        <div className="scanner-camera">
          <video ref={video} muted playsInline autoPlay />
          {!marco && <div className="scanner-frame-guide" aria-hidden="true" />}
          {marco && <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
            <polygon points={marco.map(([x, y]) => `${x * 100},${y * 100}`).join(' ')} vectorEffect="non-scaling-stroke" />
          </svg>}
        </div>}
      <div className="scanner-actions">
        {foto ? <>
          <button type="button" onClick={nuevaToma}>Repetir</button>
          <button type="button" className="scanner-primary" onClick={() => onFile(foto)}>Usar foto</button>
        </> : <>
          <button type="button" onClick={onNative}>Cámara del dispositivo</button>
          <button type="button" className="scanner-primary" disabled={!lista} onClick={() => tomar(marco)}>Tomar ahora</button>
        </>}
      </div>
    </dialog>
  )
}
