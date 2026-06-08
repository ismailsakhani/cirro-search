import type { SearchResult } from '../types/search'
import { colors, font, radius } from '../theme'
import { highlightMatch } from '../utils/highlight'

function countryFlag(iso: string | null): string {
  if (!iso || iso.length !== 2) return '✈'
  const offset = 0x1F1E6 - 65
  return (
    String.fromCodePoint(iso.toUpperCase().charCodeAt(0) + offset) +
    String.fromCodePoint(iso.toUpperCase().charCodeAt(1) + offset)
  )
}

interface Props {
  result: SearchResult
  query?: string
  onClick?: () => void
}

export function AirportCard({ result, query, onClick }: Props) {
  const code = result.iata ?? result.icao
  const flag = countryFlag(result.country)
  const cityCountry = [result.city, result.country].filter(Boolean).join(', ')

  return (
    <div style={{ ...styles.card, cursor: onClick ? 'pointer' : 'default' }} onClick={onClick}>
      <div style={styles.flag}>{flag}</div>
      <div style={styles.left}>
        <span style={styles.code}>{highlightMatch(code ?? '', query)}</span>
        {result.icao && result.iata && result.icao !== result.iata && (
          <span style={styles.icao}>{result.icao}</span>
        )}
      </div>
      <div style={styles.right}>
        <span style={styles.name}>{highlightMatch(result.name ?? result.display, query)}</span>
        {cityCountry && <span style={styles.location}>{cityCountry}</span>}
        {result.matched_fields.length > 0 && (
          <div style={styles.fields}>
            {result.matched_fields.map(f => <span key={f} style={styles.field}>{f}</span>)}
          </div>
        )}
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    display: 'flex',
    alignItems: 'center',
    gap: 14,
    background: colors.surface,
    border: `1px solid ${colors.border}`,
    borderRadius: radius.lg,
    padding: '14px 16px',
  },
  flag: {
    fontSize: 22,
    lineHeight: 1,
    flexShrink: 0,
  },
  left: {
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
    minWidth: 52,
  },
  code: {
    fontSize: 20,
    fontFamily: font.mono,
    fontWeight: 700,
    color: colors.accent,
    lineHeight: 1,
  },
  icao: {
    fontSize: 11,
    fontFamily: font.mono,
    color: colors.textDim,
  },
  score: {
    fontSize: 10,
    fontFamily: font.mono,
    color: colors.score,
    marginTop: 2,
  },
  right: {
    display: 'flex',
    flexDirection: 'column',
    gap: 3,
    flex: 1,
  },
  name: {
    fontSize: 15,
    color: colors.text,
  },
  location: {
    fontSize: 12,
    color: colors.textMuted,
    fontFamily: font.mono,
  },
  fields: {
    display: 'flex',
    gap: 4,
    flexWrap: 'wrap',
    marginTop: 2,
  },
  field: {
    fontSize: 10,
    fontFamily: font.mono,
    color: colors.matchedField,
    background: colors.matchedFieldBg,
    border: `1px solid ${colors.matchedFieldBorder}`,
    borderRadius: radius.sm - 1,
    padding: '1px 5px',
  },
}
