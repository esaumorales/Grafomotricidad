import { ESCALA_EDUCATIVA, nivelEducativo } from '../nivelEducativo'

export default function NivelEducativo({ percentil, provisional = false, puntos, total = 15 }) {
  const resultado = nivelEducativo(percentil)
  return <section className="educational-level" aria-label="Resultado global de la evaluación">
    <div className="educational-level-heading"><div><span className="educational-level-caption">Resultado de la evaluación{provisional ? ' · Provisional' : ''}</span><div className="educational-level-value">{resultado && <strong className="educational-level-letter">{resultado.letra}</strong>}<h2>{resultado?.nivel ?? 'Sin equivalencia'}</h2></div><p>{resultado ? `Según el percentil total ${percentil}.` : 'La tabla compartida no asigna un nivel a este percentil.'}</p></div>
    <div className="educational-summary-metrics"><div><strong>{puntos ?? '—'}<small> / {total}</small></strong><span>figuras logradas</span></div><div><strong>{percentil ?? '—'}</strong><span>percentil</span></div></div>
    <details><summary>Ver escala</summary><ul>{ESCALA_EDUCATIVA.map((fila) => <li key={fila.letra}><strong>{fila.letra}</strong><span>{fila.nivel}</span><span>{fila.desde}–{fila.hasta}</span></li>)}</ul></details></div>
  </section>
}
