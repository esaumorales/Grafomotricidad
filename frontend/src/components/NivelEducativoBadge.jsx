import { nivelEducativo } from '../nivelEducativo'

export default function NivelEducativoBadge({ percentil }) {
  const resultado = nivelEducativo(percentil)
  const color = !resultado ? '' : resultado.letra === 'C' ? 'support' : resultado.letra === 'B' ? 'review' : 'adequate'
  return <span className={`history-level ${color}`}><span aria-hidden="true" />{resultado ? `${resultado.letra} · ${resultado.nivel}` : 'Sin equivalencia'}</span>
}
