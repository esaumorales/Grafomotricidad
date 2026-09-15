const PATHS = {
  F01: <path d="M20 8v24" />,
  F02: <path d="M8 15h24M8 25h18" />,
  F03: <path d="M20 8v24M8 20h24" />,
  F04: <ellipse cx="20" cy="20" rx="12" ry="10" />,
  F05: <rect x="9" y="9" width="22" height="22" rx="2" />,
  F06: <polygon points="20,8 32,31 8,31" />,
  F07: <path d="M9 9l22 22M31 9 9 31" />,
  F08: <path d="M7 20c3-8 7-8 10 0s7 8 10 0 7-8 10 0" />,
  F09: (
    <>
      <rect x="6" y="12" width="28" height="16" />
      <line x1="6" y1="12" x2="34" y2="28" />
      <line x1="34" y1="12" x2="6" y2="28" />
    </>
  ),
  F10: <polygon points="20,8 32,20 20,32 8,20" />,
  F11: (
    <>
      <circle cx="20" cy="13" r="6" />
      <polygon points="20,19 30,35 10,35" />
    </>
  ),
  F12: <path d="M9 30h22M13 14v9a7 7 0 0 0 14 0v-9" />,
  F13: <path d="M12 12c-6 4-6 12 0 16c3-8 1-16-8-16m24 0c6 4 6 12 0 16c-3-8-1-16 8-16" />,
  F14: (
    <>
      <path d="M9 17 20 8l11 9" />
      <path d="M6 24c3-6 6-6 9 0s6 6 9 0 6-6 9 0" />
    </>
  ),
  F15: (
    <>
      <rect x="6" y="6" width="18" height="18" rx="2" />
      <circle cx="26" cy="26" r="9" />
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
