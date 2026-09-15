/** Placeholder de carga: barras suaves con animación, en vez de un "Cargando…" seco. */
export function Cargando({ filas = 3 }) {
  return (
    <div role="status" aria-live="polite" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <span className="visually-hidden">Cargando…</span>
      {Array.from({ length: filas }).map((_, i) => (
        <div
          key={i}
          aria-hidden="true"
          className="skeleton"
          style={{ height: 22, width: `${85 - i * 12}%`, borderRadius: 8 }}
        />
      ))}
      <style>{`
        .skeleton {
          background: linear-gradient(90deg, var(--surface-alt) 25%, var(--border) 37%, var(--surface-alt) 63%);
          background-size: 400% 100%;
          animation: skeleton-pulso 1.4s ease infinite;
        }
        @keyframes skeleton-pulso {
          0% { background-position: 100% 50%; }
          100% { background-position: 0 50%; }
        }
        @media (prefers-reduced-motion: reduce) {
          .skeleton { animation: none; }
        }
      `}</style>
    </div>
  )
}

/** Aviso de error con botón para reintentar la misma carga. */
export function ErrorConReintento({ mensaje, onReintentar }) {
  return (
    <div
      role="alert"
      style={{
        background: 'var(--yellow-light)', color: 'var(--yellow-dark)', padding: 20,
        borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center',
        justifyContent: 'space-between', gap: 16, flexWrap: 'wrap',
      }}
    >
      <span style={{ fontWeight: 700 }}>{mensaje}</span>
      {onReintentar && (
        <button
          onClick={onReintentar}
          style={{
            background: 'var(--yellow-dark)', color: 'white', fontWeight: 800, fontSize: 13,
            padding: '8px 18px', borderRadius: 'var(--radius-sm)', flexShrink: 0,
          }}
        >
          Reintentar
        </button>
      )}
    </div>
  )
}
