import { Link, useLocation } from 'react-router-dom'
import { IconMas, IconReloj, LogoTrazo } from './icons'

const ITEMS = [
  { to: '/', label: 'Nueva evaluación', Icon: IconMas, match: (p) => p === '/' },
  { to: '/historial', label: 'Historial', Icon: IconReloj, match: (p) => p.startsWith('/historial') },
]

export default function Sidebar() {
  const { pathname } = useLocation()
  return (
    <nav className="sidebar" aria-label="Navegación principal">
      <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '0 6px' }}>
        <LogoTrazo aria-hidden="true" />
        <div style={{ fontFamily: "'Baloo 2'", fontWeight: 800, fontSize: 22, color: 'var(--peach-dark)' }}>
          Trazo
        </div>
      </Link>

      <div className="sidebar-nav">
        {ITEMS.map(({ to, label, Icon, match }) => {
          const activo = match(pathname)
          return (
            <Link
              key={to}
              to={to}
              aria-current={activo ? 'page' : undefined}
              style={{
                display: 'flex', alignItems: 'center', gap: 12, padding: '13px 16px',
                borderRadius: 'var(--radius-md)', fontWeight: activo ? 800 : 700,
                color: activo ? 'var(--peach-dark)' : 'var(--text-muted)',
                background: activo ? 'var(--surface)' : 'transparent',
                boxShadow: activo ? 'var(--shadow)' : 'none',
              }}
            >
              <Icon aria-hidden="true" />
              <span className="nav-label">{label}</span>
            </Link>
          )
        })}
      </div>

      <div className="sidebar-footer">
        <div
          aria-hidden="true"
          style={{
            width: 36, height: 36, borderRadius: '50%', background: 'var(--mint-icon)',
            color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontWeight: 800, fontFamily: "'Baloo 2'", flexShrink: 0,
          }}
        >
          MR
        </div>
        <div className="sidebar-footer-texto">
          <div style={{ fontWeight: 800, fontSize: 13 }}>Milagros Rojas</div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Docente de inicial</div>
        </div>
      </div>
    </nav>
  )
}
