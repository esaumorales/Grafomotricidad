function semilla(codigo) {
  let h = 2166136261
  for (const c of String(codigo)) h = Math.imul(h ^ c.charCodeAt(0), 16777619)
  return h >>> 0
}

export default function AvatarNino({ codigo }) {
  const h = semilla(codigo)
  const piel = ['#F4C9A8', '#DFA47C', '#BC805A', '#986144', '#EAC4AD', '#C68E71'][(h >>> 3) % 6]
  const pelo = ['#382F2B', '#594334', '#292D35', '#794D32'][(h >>> 7) % 4]
  const fondo = ['#EAF0F5', '#FFF2C8', '#E6F0E9', '#EDEAF3'][(h >>> 11) % 4]
  const peinado = (h >>> 15) % 3
  const gafas = (h >>> 19) % 4 === 0
  return <svg className="child-avatar" viewBox="0 0 64 64" aria-hidden="true" focusable="false" style={{'--avatar-delay': `${h % 6}s`}}>
    <rect width="64" height="64" rx="18" fill={fondo}/>
    <g className="child-avatar-face"><path d="M12 64c0-13 8-19 20-19s20 6 20 19" fill={['#0A365B','#55786B','#7D657E'][(h >>> 9) % 3]}/>
      <circle cx="15" cy="31" r="5" fill={piel}/><circle cx="49" cy="31" r="5" fill={piel}/>
      <rect x="15" y="12" width="34" height="37" rx="16" fill={piel}/>
      {peinado === 0 ? <path d="M15 28V20c0-15 34-18 34 2v6l-6-10c-7 8-15 1-22 5l-6 5" fill={pelo}/> : peinado === 1 ? <path d="M14 29c-6-13 4-22 18-22s24 10 18 23l-5-11c-9 4-17 4-25 0z" fill={pelo}/> : <path d="M14 29V20c0-16 35-18 36 1v9l-7-10-6-5-3 7-7-5-7 6z" fill={pelo}/>}
      <g className="child-avatar-eyes" fill="#302D2B"><circle cx="25" cy="31" r="1.8"/><circle cx="39" cy="31" r="1.8"/></g>
      <path d={(h >>> 22) % 2 ? 'M26 39q6 5 12 0' : 'M28 40q4 3 8 0'} fill="none" stroke="#795042" strokeWidth="1.6" strokeLinecap="round"/>
      {gafas && <g fill="none" stroke={pelo} strokeWidth="1.4"><rect x="19" y="27" width="11" height="9" rx="3"/><rect x="34" y="27" width="11" height="9" rx="3"/><path d="M30 30h4"/></g>}
    </g>
  </svg>
}
