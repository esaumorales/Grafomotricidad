import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { IconMas, IconReloj } from './icons'

const ITEMS = [
  { to: '/', label: 'Nueva evaluación', Icon: IconMas, match: (p) => p === '/' },
  { to: '/historial', label: 'Historial', Icon: IconReloj, match: (p) => p !== '/' },
]

export default function Sidebar() {
  const { pathname } = useLocation()
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem('trazo-sidebar') === 'collapsed')
  const [mobileOpen, setMobileOpen] = useState(false)

  function toggleCollapsed() {
    setCollapsed((previous) => {
      localStorage.setItem('trazo-sidebar', previous ? 'expanded' : 'collapsed')
      return !previous
    })
  }

  return (
    <aside className={`sidebar ${collapsed ? 'is-collapsed' : ''} ${mobileOpen ? 'is-open' : ''}`} onKeyDown={(event) => { if (event.key === 'Escape') { setMobileOpen(false); event.currentTarget.querySelector('.mobile-menu-toggle')?.focus() } }}>
      <div className="sidebar-top">
        <Link to="/" className="sidebar-brand" onClick={() => setMobileOpen(false)} aria-label="Trazo, nueva evaluación">
          <span className="brand-mark" aria-hidden="true">t.</span><span className="brand-name">Trazo</span>
        </Link>
        <button type="button" className="sidebar-toggle desktop-menu-toggle" onClick={toggleCollapsed} aria-expanded={!collapsed} aria-controls="main-navigation" aria-label={collapsed ? 'Expandir menú lateral' : 'Contraer menú lateral'} title={collapsed ? 'Expandir menú' : 'Contraer menú'}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/></svg>
        </button>
        <button type="button" className="sidebar-toggle mobile-menu-toggle" onClick={() => setMobileOpen((open) => !open)} aria-expanded={mobileOpen} aria-controls="main-navigation">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d={mobileOpen ? 'M6 6l12 12M6 18L18 6' : 'M4 6h16M4 12h16M4 18h16'}/></svg>
          {mobileOpen ? 'Cerrar' : 'Menú'}
        </button>
      </div>
      <div className="sidebar-nav-panel"><nav className="sidebar-nav" id="main-navigation" aria-label="Navegación principal">
        <p className="nav-caption">Evaluaciones</p>
        {ITEMS.map(({ to, label, Icon, match }) => (
          <Link key={to} to={to} onClick={() => setMobileOpen(false)} aria-current={match(pathname) ? 'page' : undefined} aria-label={label} title={collapsed ? label : undefined}>
            <Icon aria-hidden="true" /><span className="nav-label">{label}</span>
          </Link>
        ))}
      </nav></div>
      <div className="sidebar-note"><span className="sidebar-note-short" aria-hidden="true">G</span><span className="sidebar-note-full">Evaluación grafomotora</span></div>
    </aside>
  )
}
