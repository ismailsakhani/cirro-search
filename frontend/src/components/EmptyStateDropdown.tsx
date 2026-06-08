import { useEffect, useState } from 'react'
import type { RecentSearch } from '../hooks/useRecentSearches'
import { colors, font, radius } from '../theme'

interface TrendingQuery {
  query: string
  count: number
}

interface Props {
  recents: RecentSearch[]
  onSelectRecent: (r: RecentSearch) => void
  onRemoveRecent: (id: string) => void
  onSelectTrending: (q: string) => void
}

const TYPE_ICON: Record<string, string> = {
  airport: '✈',
  flight: '→',
  gate: '▣',
}

export function EmptyStateDropdown({ recents, onSelectRecent, onRemoveRecent, onSelectTrending }: Props) {
  const [trending, setTrending] = useState<TrendingQuery[]>([])

  useEffect(() => {
    fetch('/api/v1/trending?limit=8')
      .then(r => r.ok ? r.json() : { queries: [] })
      .then(d => setTrending(d.queries ?? []))
      .catch(() => {}) // never break UI if trending fails
  }, [])

  const hasRecents = recents.length > 0
  const hasTrending = trending.length > 0

  if (!hasRecents && !hasTrending) return null

  return (
    <div style={styles.dropdown}>

      {hasRecents && (
        <div style={styles.section}>
          <div style={styles.sectionLabel}>Recent</div>
          {recents.slice(0, 5).map(r => (
            <div key={r.id} style={styles.row}>
              <button
                style={styles.rowBtn}
                onMouseDown={(e) => {
                  e.preventDefault() // prevents input blur before this fires
                  onSelectRecent(r)
                }}
              >
                <span style={styles.icon}>{TYPE_ICON[r.type] ?? '·'}</span>
                <span style={styles.display}>{r.display}</span>
                <span style={styles.type}>{r.type}</span>
              </button>
              <button
                style={styles.removeBtn}
                onMouseDown={(e) => {
                  e.preventDefault()
                  onRemoveRecent(r.id)
                }}
                aria-label="Remove"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      {hasTrending && (
        <div style={styles.section}>
          <div style={styles.sectionLabel}>Trending</div>
          {trending.map(t => (
            <button
              key={t.query}
              style={styles.trendingBtn}
              onMouseDown={(e) => {
                e.preventDefault()
                onSelectTrending(t.query)
              }}
            >
              <span style={styles.trendIcon}>↑</span>
              <span style={styles.display}>{t.query}</span>
              <span style={styles.count}>{t.count} search{t.count !== 1 ? 'es' : ''}</span>
            </button>
          ))}
        </div>
      )}

    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  dropdown: {
    position: 'absolute',
    top: '100%',
    left: 0,
    right: 0,
    zIndex: 20,
    marginTop: 4,
    background: colors.surface,
    border: `1px solid ${colors.border}`,
    borderRadius: radius.md,
    overflow: 'hidden',
    boxShadow: '0 4px 24px rgba(0,0,0,0.4)',
  },
  section: {
    borderBottom: `1px solid ${colors.panel}`,
  },
  sectionLabel: {
    fontFamily: font.mono,
    fontSize: 10,
    color: colors.textDim,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.08em',
    padding: '8px 14px 4px',
  },
  row: {
    display: 'flex',
    alignItems: 'center',
    borderTop: `1px solid ${colors.panel}`,
  },
  rowBtn: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    background: 'none',
    border: 'none',
    padding: '9px 14px',
    cursor: 'pointer',
    textAlign: 'left' as const,
    fontFamily: font.mono,
  },
  icon: {
    fontSize: 13,
    color: colors.textDim,
    width: 16,
    textAlign: 'center' as const,
    flexShrink: 0,
  },
  display: {
    flex: 1,
    fontSize: 13,
    color: colors.text,
    fontFamily: font.mono,
  },
  type: {
    fontSize: 11,
    color: colors.textFaint,
    fontFamily: font.mono,
  },
  removeBtn: {
    background: 'none',
    border: 'none',
    color: colors.textFaint,
    fontSize: 16,
    cursor: 'pointer',
    padding: '0 14px',
    lineHeight: 1,
    flexShrink: 0,
    fontFamily: font.mono,
  },
  trendingBtn: {
    width: '100%',
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    background: 'none',
    border: 'none',
    borderTop: `1px solid ${colors.panel}`,
    padding: '9px 14px',
    cursor: 'pointer',
    textAlign: 'left' as const,
    fontFamily: font.mono,
  },
  trendIcon: {
    fontSize: 11,
    color: colors.textDim,
    width: 16,
    textAlign: 'center' as const,
    flexShrink: 0,
  },
  count: {
    fontSize: 11,
    color: colors.textFaint,
    fontFamily: font.mono,
    flexShrink: 0,
  },
}
