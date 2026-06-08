import { useState } from 'react'
import type { SearchResult } from '../types/search'
import { colors, font, radius } from '../theme'

interface Props {
  results: SearchResult[]
  onSelect: (display: string) => void
}

const TYPE_ICON: Record<string, string> = {
  airport: '✈',
  flight: '→',
  gate: '▣',
}

export function SuggestionList({ results, onSelect }: Props) {
  const [hovered, setHovered] = useState<number | null>(null)
  const visible = results.slice(0, 6)

  if (!visible.length) return null

  return (
    <ul style={styles.list}>
      {visible.map((r, i) => (
        <li
          key={r.id ?? i}
          style={{
            ...styles.item,
            background: hovered === i ? '#1e1e3a' : 'transparent',
          }}
          onClick={() => onSelect(r.display)}
          onMouseEnter={() => setHovered(i)}
          onMouseLeave={() => setHovered(null)}
        >
          <span style={styles.icon}>{TYPE_ICON[r.type] ?? '·'}</span>
          <span style={styles.display}>{r.display}</span>
          <span style={styles.type}>{r.type}</span>
        </li>
      ))}
    </ul>
  )
}

const styles: Record<string, React.CSSProperties> = {
  list: {
    listStyle: 'none',
    margin: 0,
    padding: 0,
    border: `1px solid ${colors.border}`,
    borderRadius: radius.md,
    background: colors.surface,
    overflow: 'hidden',
    position: 'absolute',
    top: '100%',
    left: 0,
    right: 0,
    zIndex: 10,
    marginTop: 2,
    boxShadow: '0 4px 24px rgba(0,0,0,0.4)',
  },
  item: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '9px 14px',
    cursor: 'pointer',
    borderBottom: `1px solid ${colors.panel}`,
    fontSize: 14,
    fontFamily: font.mono,
    transition: 'background 0.1s',
  },
  icon: {
    color: colors.textDim,
    fontSize: 13,
    width: 16,
    textAlign: 'center',
    flexShrink: 0,
  },
  display: {
    flex: 1,
    color: colors.text,
  },
  type: {
    color: colors.textFaint,
    fontSize: 11,
  },
}
