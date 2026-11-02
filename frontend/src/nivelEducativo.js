// Equivalencia solicitada por el usuario; conservar los intervalos de su tabla.
export const ESCALA_EDUCATIVA = [
  { letra: 'AD', nivel: 'Logro destacado', desde: 80, hasta: 99 },
  { letra: 'A', nivel: 'Logro esperado', desde: 55, hasta: 75 },
  { letra: 'B', nivel: 'En proceso', desde: 30, hasta: 50 },
  { letra: 'C', nivel: 'En inicio', desde: 1, hasta: 25 },
]
export function nivelEducativo(percentil) {
  if (percentil == null || percentil === '' || !Number.isFinite(Number(percentil))) return null
  const valor = Number(percentil)
  return ESCALA_EDUCATIVA.find(({ desde, hasta }) => valor >= desde && valor <= hasta) ?? null
}
