// Debe coincidir con `config/config.yaml > figuras` del backend (orden y nombres).
export const FIGURAS = [
  { id: 'F01', numero: 1, nombre: 'Línea recta' },
  { id: 'F02', numero: 2, nombre: 'Dos líneas' },
  { id: 'F03', numero: 3, nombre: 'Cruz' },
  { id: 'F04', numero: 4, nombre: 'Círculo' },
  { id: 'F05', numero: 5, nombre: 'Cuadrado' },
  { id: 'F06', numero: 6, nombre: 'Triángulo' },
  { id: 'F07', numero: 7, nombre: 'X (aspa)' },
  { id: 'F08', numero: 8, nombre: 'Línea ondulada' },
  { id: 'F09', numero: 9, nombre: 'Rectángulo + X' },
  { id: 'F10', numero: 10, nombre: 'Rombo' },
  { id: 'F11', numero: 11, nombre: 'Círculo + triángulo' },
  { id: 'F12', numero: 12, nombre: 'U' },
  { id: 'F13', numero: 13, nombre: 'Lazo' },
  { id: 'F14', numero: 14, nombre: 'Doble pico ondulado' },
  { id: 'F15', numero: 15, nombre: 'Cuadrado + círculo' },
]

export const FIGURA_POR_ID = Object.fromEntries(FIGURAS.map((f) => [f.id, f]))
