import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { SearchResponse, SuggestionResponse, SearchResult } from '../types/search'
import type { RecentSearch } from '../hooks/useRecentSearches'
import { recordSelection } from '../api/feedbackClient'
import { colors, font, radius } from '../theme'
import { AirportCard } from './AirportCard'
import { FlightCard } from './FlightCard'
import { GateCard } from './GateCard'

const FEATURED = ['heathrow', 'ua44', 'cdg', 'ewr c101', 'dubai', 'hong kong', '4433', 'kewr']

const TYPE_ICON: Record<string, string> = { airport: '✈', flight: '→', gate: '▣' }

interface TrendingQuery { query: string; count: number }

interface Props {
  result: SearchResponse | SuggestionResponse | null
  error: string | null
  loading?: boolean
  saveRecent?: (result: SearchResult, query: string) => void
  recents?: RecentSearch[]
  trending?: TrendingQuery[]
  onEmptySelect?: (q: string) => void
  onRemoveRecent?: (id: string) => void
}

function SkeletonCard() {
  return (
    <div style={styles.skeletonCard}>
      <div style={{ ...styles.skeletonBlock, width: 32, height: 32, borderRadius: radius.sm }} />
      <div style={styles.skeletonRight}>
        <div style={{ ...styles.skeletonBlock, width: '30%', height: 14 }} />
        <div style={{ ...styles.skeletonBlock, width: '60%', height: 11 }} />
      </div>
    </div>
  )
}

function ResultCard({ result, debug, query, onClick }: { result: SearchResult; debug: SearchResponse['debug']; query: string; onClick: () => void }) {
  if (result.type === 'airport') return <AirportCard result={result} query={query} onClick={onClick} />
  if (result.type === 'flight') return <FlightCard result={result} query={query} onClick={onClick} />
  if (result.type === 'gate') return <GateCard result={result} query={query} onClick={onClick} />
  return (
    <div style={{ ...styles.fallbackCard, cursor: 'pointer' }} onClick={onClick}>
      <span style={styles.fallbackType}>{result.type}</span>
      <span style={styles.fallbackDisplay}>{result.display}</span>
    </div>
  )
}

export function ResultPanel({ result, error, loading, saveRecent, recents = [], trending = [], onEmptySelect, onRemoveRecent }: Props) {
  const [showDebug, setShowDebug] = useState(false)
  const navigate = useNavigate()

  if (loading && !result) {
    return (
      <div style={styles.cards}>
        <SkeletonCard />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ ...styles.errorBanner }}>
        <span style={styles.errorText}>{error}</span>
      </div>
    )
  }

  if (!result) {
    const hasRecents = recents.length > 0
    const hasTrending = trending.length > 0
    const showFeatured = !hasRecents && !hasTrending

    return (
      <div style={styles.discoveryPanel}>
        {hasRecents && (
          <div style={styles.discoverySection}>
            <div style={styles.discoverySectionLabel}>Recent</div>
            {recents.slice(0, 5).map(r => (
              <div key={r.id} style={styles.discoveryRow}>
                <button style={styles.discoveryBtn} onClick={() => onEmptySelect?.(r.query)}>
                  <span style={styles.discoveryIcon}>{TYPE_ICON[r.type] ?? '·'}</span>
                  <span style={styles.discoveryDisplay}>{r.display}</span>
                  <span style={styles.discoveryType}>{r.type}</span>
                </button>
                <button style={styles.discoveryRemove} onClick={() => onRemoveRecent?.(r.id)} aria-label="Remove">×</button>
              </div>
            ))}
          </div>
        )}

        {hasTrending && (
          <div style={styles.discoverySection}>
            <div style={styles.discoverySectionLabel}>Trending</div>
            {trending.slice(0, 6).map(t => (
              <button key={t.query} style={styles.discoveryTrendBtn} onClick={() => onEmptySelect?.(t.query)}>
                <span style={styles.discoveryIcon}>↑</span>
                <span style={styles.discoveryDisplay}>{t.query}</span>
                <span style={styles.discoveryType}>{t.count} search{t.count !== 1 ? 'es' : ''}</span>
              </button>
            ))}
          </div>
        )}

        {showFeatured && (
          <div style={styles.discoverySection}>
            <div style={styles.discoverySectionLabel}>Try these</div>
            <div style={styles.featuredChips}>
              {FEATURED.map(q => (
                <button key={q} style={styles.featuredChip} onClick={() => onEmptySelect?.(q)}>{q}</button>
              ))}
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div style={styles.root}>
      <div style={styles.statsRow}>
        <span style={styles.badge}>{result.results.length} result{result.results.length !== 1 ? 's' : ''}</span>
        <span style={styles.badge}>{result.debug.pipeline_took_ms}ms</span>
        <span style={styles.badgeMuted}>{result.debug.provider_took_ms}ms ES</span>
        {result.debug.fallback_used && <span style={styles.badgeGreen}>fallback</span>}
        <button style={styles.debugBtn} onClick={() => setShowDebug(v => !v)}>
          {showDebug ? 'hide debug' : 'show debug'}
        </button>
      </div>

      {result.results.length === 0 && (
        <div style={styles.noResults}>
          No results for &ldquo;{result.query}&rdquo; — try a different query
        </div>
      )}

      <div style={styles.cards}>
        {result.results.map((r, i) => (
          <ResultCard
            key={r.id ?? i}
            result={r}
            debug={result.debug}
            query={result.query}
            onClick={() => {
              recordSelection(r.id)
              saveRecent?.(r, result.query)
              navigate('/result', { state: { result: r, debug: result.debug, query: result.query } })
            }}
          />
        ))}
      </div>

      {showDebug && (
        <DebugPanel result={result} />
      )}
    </div>
  )
}

const QUERY_TYPE_LABEL: Record<string, string> = {
  AIRPORT_IATA: 'Airport code — IATA (3-letter code like CDG, LHR, JFK)',
  AIRPORT_ICAO: 'Airport code — ICAO (4-letter code like LFPG, EGLL, KJFK)',
  FLIGHT: 'Flight number (airline code + number, e.g. UA44, BA117)',
  GATE: 'Gate identifier (e.g. C101, A12, B7)',
  DIGITS: 'Numeric flight number only (e.g. "44" — no airline prefix)',
  AMBIGUOUS: 'Name or city — treated as a text search',
  UNKNOWN: 'Unrecognized pattern — broad keyword search',
}

const EXPLANATION_LABEL: Record<string, { label: string; detail: string }> = {
  es_score:             { label: 'Text relevance',        detail: 'Elasticsearch scored how well the document matches the search terms' },
  exact_iata:           { label: 'Exact airport code',    detail: 'The IATA code matched exactly (e.g. "cdg" → CDG)' },
  exact_icao:           { label: 'Exact ICAO code',       detail: 'The ICAO code matched exactly (e.g. "lfpg" → LFPG)' },
  exact_iata_flight:    { label: 'Exact flight code',     detail: 'The IATA flight identifier matched exactly (e.g. "ua44" → UA44)' },
  exact_icao_flight:    { label: 'Exact ICAO flight',     detail: 'The ICAO flight identifier matched exactly' },
  exact_gate:           { label: 'Exact gate',            detail: 'The gate identifier matched exactly' },
  exact_flight_number:  { label: 'Exact flight number',   detail: 'The numeric flight number matched exactly' },
  type_alignment:       { label: 'Correct result type',   detail: 'This result is the type cirro-search expected (e.g. searching a flight code → flight result)' },
  alias_entity_match:   { label: 'Known alias match',     detail: 'This result was pinned because you used a known alternate name (e.g. "heathrow" → LHR)' },
  digits_match:         { label: 'Flight number digits',  detail: 'The numeric part of the query matched this flight\'s number' },
  searchable_text_match:{ label: 'Name/text match',       detail: 'The query was found somewhere in the airport or flight name' },
  popularity:           { label: 'Popularity boost',      detail: 'High-traffic airport or flight — ranked slightly higher' },
}

function DebugPanel({ result }: { result: SearchResponse | SuggestionResponse }) {
  const cls = result.debug.classification
  const top = result.results[0]

  return (
    <div style={styles.debugPanel}>
      <div style={styles.debugTitle}>How cirro-search processed this query</div>

      <div style={styles.debugSection}>
        <div style={styles.debugSectionLabel}>What you typed</div>
        <DebugRow label="Raw query" value={`"${result.query}"`} />
        <DebugRow
          label="Understood as"
          value={QUERY_TYPE_LABEL[cls.query_type] ?? cls.query_type}
        />
        {cls.entity_type && (
          <DebugRow label="Searched only" value={`${cls.entity_type}s — cirro-search was confident enough to narrow the search to one type`} />
        )}
        {result.debug.alias_resolution && (
          <DebugRow
            label="Alias recognised"
            value={`"${result.query}" is a known name — resolved directly to ${result.debug.alias_resolution.entity_id}`}
          />
        )}
        {result.debug.expansions.length > 1 && (
          <DebugRow
            label="Terms searched"
            value={result.debug.expansions.join(' · ') + ' — cirro-search expanded your input to catch IATA/ICAO variants'}
          />
        )}
        {result.debug.fallback_used && (
          <DebugRow
            label="Fallback triggered"
            value="No results with type filter — cirro-search retried across all types"
            highlight
          />
        )}
      </div>

      <div style={styles.debugSection}>
        <div style={styles.debugSectionLabel}>Speed</div>
        <DebugRow label="Total time" value={`${result.debug.pipeline_took_ms} ms — time from your keystroke to results on screen`} />
        <DebugRow label="Elasticsearch" value={`${result.debug.provider_took_ms} ms — time inside the search engine`} />
        <DebugRow label="Pipeline overhead" value={`${result.debug.pipeline_took_ms - result.debug.provider_took_ms} ms — query classification, ranking, alias lookup`} />
      </div>

      {top && (
        <div style={styles.debugSection}>
          <div style={styles.debugSectionLabel}>Why "{top.display}" ranked #1</div>
          <DebugRow label="Score" value={`${top.score.toFixed(2)} — sum of all signals below; higher = more relevant`} />
          {(top.explanation ?? []).map(code => {
            const info = EXPLANATION_LABEL[code]
            return info ? (
              <DebugRow key={code} label={info.label} value={info.detail} />
            ) : (
              <DebugRow key={code} label={code} value="Internal ranking signal" />
            )
          })}
        </div>
      )}
    </div>
  )
}

function DebugRow({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div style={styles.debugRow}>
      <span style={styles.debugKey}>{label}</span>
      <span style={{ ...styles.debugVal, color: highlight ? colors.fallbackGreen : colors.textMuted }}>{value}</span>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  root: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  statsRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    flexWrap: 'wrap',
    paddingBottom: 4,
  },
  badge: {
    background: colors.panelHover,
    color: colors.accent,
    padding: '3px 8px',
    borderRadius: radius.sm,
    fontSize: 12,
    fontFamily: font.mono,
  },
  badgeMuted: {
    background: colors.surfaceAlt,
    color: colors.textDim,
    padding: '3px 8px',
    borderRadius: radius.sm,
    fontSize: 12,
    fontFamily: font.mono,
  },
  badgeGreen: {
    background: colors.fallbackGreenBg,
    color: colors.fallbackGreen,
    padding: '3px 8px',
    borderRadius: radius.sm,
    fontSize: 12,
    fontFamily: font.mono,
  },
  debugBtn: {
    marginLeft: 'auto',
    background: 'none',
    border: `1px solid ${colors.borderMuted}`,
    color: colors.textFaint,
    borderRadius: radius.sm,
    padding: '3px 10px',
    fontSize: 11,
    fontFamily: font.mono,
    cursor: 'pointer',
  },
  cards: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
  },
  fallbackCard: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    background: colors.surface,
    border: `1px solid ${colors.border}`,
    borderRadius: radius.lg,
    padding: '12px 16px',
  },
  fallbackType: {
    background: '#2a2a4a',
    color: colors.accent,
    padding: '2px 6px',
    borderRadius: radius.sm,
    fontSize: 11,
    fontFamily: font.mono,
  },
  fallbackDisplay: {
    fontSize: 14,
    color: colors.text,
    fontFamily: font.mono,
  },
  noResults: {
    color: colors.textDim,
    fontFamily: font.mono,
    fontSize: 14,
    padding: '20px 0',
    textAlign: 'center',
  },
  errorBanner: {
    border: `1px solid ${colors.errorBorder}`,
    borderRadius: radius.md,
    background: colors.errorBg,
    padding: '12px 16px',
  },
  errorText: {
    color: colors.error,
    fontFamily: font.mono,
    fontSize: 13,
  },
  empty: {
    color: colors.textDim,
    fontFamily: font.mono,
    fontSize: 14,
    padding: 24,
    textAlign: 'center',
    border: `1px dashed ${colors.borderDim}`,
    borderRadius: radius.md,
  },
  debugPanel: {
    marginTop: 8,
    border: `1px solid ${colors.border}`,
    borderRadius: radius.md,
    background: colors.surface,
    padding: '14px 16px',
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
  },
  debugTitle: {
    fontFamily: font.mono,
    fontSize: 11,
    color: colors.textDim,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.08em',
  },
  debugSection: {
    display: 'flex',
    flexDirection: 'column',
    gap: 0,
    borderLeft: `2px solid ${colors.panelHover}`,
    paddingLeft: 12,
  },
  debugSectionLabel: {
    fontFamily: font.mono,
    fontSize: 10,
    color: colors.textDim,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.08em',
    marginBottom: 6,
  },
  debugRow: {
    display: 'flex',
    gap: 12,
    padding: '5px 0',
    borderBottom: `1px solid ${colors.panel}`,
    alignItems: 'flex-start',
  },
  debugKey: {
    fontFamily: font.mono,
    fontSize: 11,
    color: colors.text,
    minWidth: 140,
    flexShrink: 0,
    paddingTop: 1,
  },
  debugVal: {
    fontFamily: font.mono,
    fontSize: 12,
    color: colors.textMuted,
    lineHeight: 1.5,
  },
  discoveryPanel: {
    border: `1px solid ${colors.border}`,
    borderRadius: radius.lg,
    background: colors.surface,
    overflow: 'hidden',
  },
  discoverySection: {
    borderBottom: `1px solid ${colors.panel}`,
  },
  discoverySectionLabel: {
    fontFamily: font.mono,
    fontSize: 10,
    color: colors.textDim,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.08em',
    padding: '10px 16px 4px',
  },
  discoveryRow: {
    display: 'flex',
    alignItems: 'center',
    borderTop: `1px solid ${colors.panel}`,
  },
  discoveryBtn: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    background: 'none',
    border: 'none',
    padding: '10px 16px',
    cursor: 'pointer',
    textAlign: 'left' as const,
  },
  discoveryTrendBtn: {
    width: '100%',
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    background: 'none',
    border: 'none',
    borderTop: `1px solid ${colors.panel}`,
    padding: '10px 16px',
    cursor: 'pointer',
    textAlign: 'left' as const,
  },
  discoveryIcon: {
    fontSize: 13,
    color: colors.textDim,
    width: 16,
    textAlign: 'center' as const,
    flexShrink: 0,
    fontFamily: font.mono,
  },
  discoveryDisplay: {
    flex: 1,
    fontSize: 14,
    color: colors.text,
    fontFamily: font.mono,
  },
  discoveryType: {
    fontSize: 11,
    color: colors.textFaint,
    fontFamily: font.mono,
  },
  discoveryRemove: {
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
  featuredChips: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: 8,
    padding: '10px 16px 14px',
  },
  featuredChip: {
    background: colors.panel,
    border: `1px solid ${colors.border}`,
    borderRadius: radius.sm,
    color: colors.accent,
    fontFamily: font.mono,
    fontSize: 12,
    padding: '4px 12px',
    cursor: 'pointer',
  },
  skeletonCard: {
    display: 'flex',
    alignItems: 'center',
    gap: 14,
    background: colors.surface,
    border: `1px solid ${colors.border}`,
    borderRadius: radius.lg,
    padding: '14px 16px',
  },
  skeletonRight: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
    flex: 1,
  },
  skeletonBlock: {
    background: colors.panelHover,
    borderRadius: radius.sm,
    animation: 'pulse 1.4s ease-in-out infinite',
  },
}
