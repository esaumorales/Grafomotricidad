/** Compara el resultado original de la IA contra el resultado ya con las correcciones
 * del docente aplicadas. Solo se muestra si el docente corrigió al menos una figura. */
export default function ComparacionIA({ sesion }) {
  const tieneCorrecciones = sesion.figuras.some((f) => f.puntaje_docente !== null)
  if (!tieneCorrecciones) return null

  const tecnico = sesion.panel_tecnico.resumen
  const pdIa = tecnico.PD_ia
  const pdDocente = tecnico.PD

  return (
    <div
      style={{
        display: 'flex', flexWrap: 'wrap', gap: 6, alignItems: 'baseline',
        background: 'var(--surface-alt)', border: '1.5px dashed var(--peach)',
        borderRadius: 'var(--radius-md)', padding: '14px 18px', fontSize: 13.5,
      }}
    >
      <span style={{ fontWeight: 800, color: 'var(--peach-dark)' }}>Con correcciones del docente:</span>
      <span style={{ color: 'var(--text-muted)' }}>
        IA: <strong style={{ color: 'var(--text)' }}>{pdIa}/15 · {tecnico.nivel_ia}</strong>
        {'  →  '}
        Docente: <strong style={{ color: 'var(--text)' }}>{pdDocente}/15 · {tecnico.nivel}</strong>
      </span>
    </div>
  )
}
