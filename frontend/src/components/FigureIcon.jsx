// Trazos medidos sobre las plantillas de la escala (lienzo de 40 x 40), para que cada ícono se parezca a su figura.
const PATHS = {
  F01: <path d="M20 4v32" />,
  F02: <path d="M4.5 15h31M5 25h30" />,
  F03: <path d="M20 6v28M4 20h32" />,
  F04: <circle cx="20" cy="20" r="16" />,
  F05: <rect x="4.5" y="5.5" width="31" height="29" />,
  F06: <polygon points="20,7 36,33 4,33" />,
  F07: <path d="M4.5 5.5l31 29M35.5 5.5l-31 29" />,
  F08: <path d="M4 19C5 13 9 12 13 12C17 12 20 15 20 20C20 25 23 28 27 28C31 28 35 25 35.5 21.5" />,
  F09: (
    <>
      <rect x="4" y="11.5" width="32" height="17" />
      <path d="M4 11.5l32 17M36 11.5l-32 17" />
    </>
  ),
  F10: <polygon points="20,4.5 32.5,20 20,35.5 7.5,20" />,
  F11: (
    <>
      <circle cx="20" cy="12" r="8" />
      <polygon points="20,20.5 28.5,35.5 11.5,35.5" />
    </>
  ),
  F12: <path d="M4 28h32M10.4 12v6a9.8 9.8 0 0 0 19.6 0v-6" />,
  F13: <path d="M4 12.6h7C17 12.6 20 15 20 20.2c0 4.8-3 7.4-9 7.4H4M36 12.6h-7C23 12.6 20 15 20 20.2c0 4.8 3 7.4 9 7.4h7" />,
  F14: (
    <>
      <path d="M10.8 30 20 10l9.2 20" />
      <path d="M4 21.5C5 17 8 16.5 11 17.5C14 18.5 15 25 20 27C25 25 26 18.5 29 17.5C32 16.5 35 17 36 21.5" />
    </>
  ),
  F15: (
    <>
      <rect x="4.5" y="4.5" width="19" height="19" />
      <circle cx="25" cy="25" r="10.6" />
    </>
  ),
}

/** Ícono geométrico en miniatura para una figura del CUMANIN, usado en las grillas. */
export default function FigureIcon({ figuraId, size = 34, color = 'currentColor', strokeWidth = 2.4 }) {
  const path = PATHS[figuraId]
  if (!path) return null
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 40 40"
      fill="none"
      stroke={color}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ display: 'block', margin: '0 auto' }}
    >
      {path}
    </svg>
  )
}
