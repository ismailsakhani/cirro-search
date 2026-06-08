import type { SearchResult } from '../types/search'
import { colors, font, radius } from '../theme'
import { highlightMatch } from '../utils/highlight'

interface Props {
  result: SearchResult
  query?: string
  onClick?: () => void
}

export function FlightCard({ result, query, onClick }: Props) {
  const primaryCode = result.iata_flight ?? result.icao_flight
  const secondaryCode =
    result.icao_flight && result.iata_flight && result.icao_flight !== result.iata_flight
      ? result.icao_flight
      : null

  const airlineName =
    result.airline_name ??
    (result.display.includes(' - ') ? result.display.split(' - ').slice(1).join(' - ') : result.airline ?? '')

  return (
    <div style={{ ...styles.card, cursor: onClick ? 'pointer' : 'default' }} onClick={onClick}>
      <div style={styles.icon}>✈</div>
      <div style={styles.left}>
        <span style={styles.code}>{highlightMatch(primaryCode ?? '', query)}</span>
        {secondaryCode && <span style={styles.secondary}>{secondaryCode}</span>}
      </div>
      <div style={styles.right}>
        <span style={styles.airline}>{highlightMatch(airlineName, query)}</span>
        {result.flight_number && (
          <span style={styles.flightNum}>Flight {result.flight_number}</span>
        )}
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
  icon: {
    fontSize: 18,
    color: colors.textDim,
    flexShrink: 0,
    width: 26,
    textAlign: 'center',
  },
  left: {
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
    minWidth: 80,
  },
  code: {
    fontSize: 20,
    fontFamily: font.mono,
    fontWeight: 700,
    color: colors.accent,
    lineHeight: 1,
  },
  secondary: {
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
  airline: {
    fontSize: 15,
    color: colors.text,
  },
  flightNum: {
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
