import { useLocation, useNavigate } from 'react-router-dom'
import type { SearchResult, SearchResponse } from '../types/search'
import { AirportCard } from '../components/AirportCard'
import { FlightCard } from '../components/FlightCard'
import { GateCard } from '../components/GateCard'
import { colors, font, radius } from '../theme'

interface LocationState {
  result: SearchResult
  debug: SearchResponse['debug']
  query: string
}

const QUERY_TYPE_LABEL: Record<string, { short: string; plain: string }> = {
  AIRPORT_IATA: {
    short: 'IATA airport code',
    plain: 'You typed a 3-letter airport code (IATA format). These are the codes you see on boarding passes — CDG for Paris, LHR for London Heathrow, JFK for New York.',
  },
  AIRPORT_ICAO: {
    short: 'ICAO airport code',
    plain: 'You typed a 4-letter airport code (ICAO format). Used by air traffic control and pilots — LFPG for Paris CDG, EGLL for London Heathrow.',
  },
  FLIGHT: {
    short: 'Flight number',
    plain: 'You typed an airline code followed by a number — cirro-search recognised this as a specific flight. It expanded the search to cover both IATA and ICAO variants of the airline code.',
  },
  GATE: {
    short: 'Gate identifier',
    plain: 'You typed a gate code (letter + number, e.g. C101). cirro-search looked for gates matching that identifier across all airports in the index.',
  },
  DIGITS: {
    short: 'Numeric flight number',
    plain: 'You typed a number only — no airline prefix. cirro-search searched for flights with that number across all airlines.',
  },
  AMBIGUOUS: {
    short: 'Text / name search',
    plain: 'Your query did not match a known code pattern, so cirro-search ran a full text search across airport names, city names, and aliases.',
  },
  UNKNOWN: {
    short: 'Broad keyword search',
    plain: 'cirro-search could not classify your query into a known pattern and ran a broad keyword search across all fields.',
  },
}

const EXPLANATION_LABEL: Record<string, { label: string; tech: string; plain: string }> = {
  es_score: {
    label: 'Text relevance',
    tech: 'Elasticsearch BM25 relevance score for term frequency and field boosting',
    plain: 'The search engine scored how closely the document\'s text matched your query terms.',
  },
  exact_iata: {
    label: 'Exact IATA code',
    tech: 'Keyword field exact match on iata — boost +200',
    plain: 'The 3-letter IATA code matched your query exactly. This is the strongest signal for airport lookups.',
  },
  exact_icao: {
    label: 'Exact ICAO code',
    tech: 'Keyword field exact match on icao — boost +200',
    plain: 'The 4-letter ICAO code matched your query exactly.',
  },
  exact_iata_flight: {
    label: 'Exact IATA flight code',
    tech: 'Keyword field exact match on iata_flight — boost +200',
    plain: 'The full IATA flight identifier (e.g. UA44) matched exactly. Highest confidence match for flight lookups.',
  },
  exact_icao_flight: {
    label: 'Exact ICAO flight code',
    tech: 'Keyword field exact match on icao_flight — boost +200',
    plain: 'The full ICAO flight identifier matched exactly.',
  },
  exact_gate: {
    label: 'Exact gate match',
    tech: 'Keyword field exact match on gate — boost +200',
    plain: 'The gate identifier matched your query exactly.',
  },
  exact_flight_number: {
    label: 'Exact flight number',
    tech: 'Keyword field exact match on flight_number (digits only) — boost +100',
    plain: 'The numeric part of the flight number matched exactly (e.g. "44" for UA44).',
  },
  type_alignment: {
    label: 'Correct result type',
    tech: 'Entity type matches classification.entity_type — boost +50',
    plain: 'This result is the same type cirro-search expected from your query. Searching a flight code and getting a flight result — no type mismatch.',
  },
  alias_entity_match: {
    label: 'Known alias pinned',
    tech: 'Preferred entity ID matched alias resolver — boost +1000',
    plain: 'You used a well-known name (like "heathrow" or "charles de gaulle") that cirro-search has mapped directly to a specific airport. This result was pinned to the top.',
  },
  digits_match: {
    label: 'Flight number digits',
    tech: 'classification.digits matched document.flight_number — boost +75',
    plain: 'The number you typed matched the numeric part of this flight\'s number.',
  },
  searchable_text_match: {
    label: 'Name or description match',
    tech: 'Query found in searchable_text field (substring) — boost +25',
    plain: 'Your query appeared somewhere in the full text of this result\'s name, city, or description.',
  },
  popularity: {
    label: 'Popularity boost',
    tech: 'metadata.popularity * 0.1 added to score',
    plain: 'This is a high-traffic airport or frequently searched flight — given a small ranking boost.',
  },
}

function EntityCard({ result }: { result: SearchResult }) {
  if (result.type === 'airport') return <AirportCard result={result} />
  if (result.type === 'flight') return <FlightCard result={result} />
  if (result.type === 'gate') return <GateCard result={result} />
  return null
}

function Section({ title }: { title: string }) {
  return <div style={styles.sectionTitle}>{title}</div>
}

function Row({ label, tech, plain }: { label: string; tech: string; plain: string }) {
  return (
    <div style={styles.row}>
      <div style={styles.rowLabel}>{label}</div>
      <div style={styles.rowBody}>
        <div style={styles.rowTech}>{tech}</div>
        <div style={styles.rowPlain}>{plain}</div>
      </div>
    </div>
  )
}

export function ResultDetail() {
  const location = useLocation()
  const navigate = useNavigate()
  const state = location.state as LocationState | null

  if (!state) {
    return (
      <div style={styles.page}>
        <div style={styles.notFound}>No result selected. <span style={styles.back} onClick={() => navigate('/')}>← Back to search</span></div>
      </div>
    )
  }

  const { result, debug, query } = state
  const cls = debug.classification
  const queryTypeInfo = QUERY_TYPE_LABEL[cls.query_type]

  return (
    <div style={styles.page}>
      <div style={styles.topBar}>
        <button style={styles.backBtn} onClick={() => navigate(-1)}>← Back to results</button>
        <span style={styles.topQuery}>Query: <span style={styles.topQueryVal}>"{query}"</span></span>
      </div>

      <div style={styles.card}>
        <EntityCard result={result} />
      </div>

      <div style={styles.panel}>

        {/* ── WHAT YOU SEARCHED ── */}
        <Section title="What you searched" />
        <Row
          label="Query type"
          tech={cls.query_type}
          plain={queryTypeInfo?.plain ?? cls.query_type}
        />
        <Row
          label="Normalised to"
          tech={cls.normalized_query}
          plain={`cirro-search stripped extra spaces and lowercased your input before processing.`}
        />
        {cls.entity_type && (
          <Row
            label="Type filter applied"
            tech={`entity_type = ${cls.entity_type}`}
            plain={`cirro-search was confident your query refers to a ${cls.entity_type}, so it restricted results to that type only. This improves precision.`}
          />
        )}
        {debug.alias_resolution && (
          <Row
            label="Alias resolved"
            tech={`term → ${debug.alias_resolution.entity_id}`}
            plain={`"${query}" is a recognised common name. cirro-search mapped it directly to a known entity without relying purely on text matching.`}
          />
        )}
        {debug.expansions.length > 1 && (
          <Row
            label="Search terms used"
            tech={debug.expansions.join(', ')}
            plain={`cirro-search expanded your input to cover alternate formats (IATA/ICAO variants, flight number digits). All these terms were searched simultaneously.`}
          />
        )}
        {debug.fallback_used && (
          <Row
            label="Fallback triggered"
            tech="entity_type filter dropped on retry"
            plain="The first search (with the type filter) returned zero results. cirro-search automatically retried without the filter to avoid showing a blank page."
          />
        )}

        {/* ── WHY THIS RESULT RANKED WHERE IT DID ── */}
        <Section title={`Why "${result.display}" ranked here`} />
        <Row
          label="Relevance score"
          tech={result.score.toFixed(2)}
          plain="cirro-search adds up multiple signals below to get this number. Higher = more relevant. Results are sorted by this score, highest first."
        />
        {(result.explanation ?? []).map(code => {
          const info = EXPLANATION_LABEL[code]
          return info ? (
            <Row key={code} label={info.label} tech={info.tech} plain={info.plain} />
          ) : (
            <Row key={code} label={code} tech={code} plain="Internal ranking signal." />
          )
        })}
        {(result.explanation ?? []).length === 0 && (
          <Row
            label="Ranking signals"
            tech="not available"
            plain="Restart the backend to see per-signal breakdown — this requires the updated server that returns explanation data."
          />
        )}

        {/* ── MATCHED FIELDS ── */}
        {result.matched_fields.length > 0 && (
          <>
            <Section title="Where in the document the match was found" />
            <Row
              label="Matched fields"
              tech={result.matched_fields.join(', ')}
              plain={`Elasticsearch found your query in these document fields: ${result.matched_fields.join(', ')}. Fields like "iata" and "iata_flight" are exact codes. "searchable_text" is the combined name/city/alias blob.`}
            />
          </>
        )}

        {/* ── SPEED ── */}
        <Section title="Performance" />
        <Row
          label="Total pipeline time"
          tech={`${debug.pipeline_took_ms} ms`}
          plain="End-to-end time from API call to ranked results returned — includes classification, alias lookup, Elasticsearch query, and ranking."
        />
        <Row
          label="Elasticsearch time"
          tech={`${debug.provider_took_ms} ms`}
          plain="Time spent inside Elasticsearch executing the query. The rest is Python pipeline overhead."
        />
        <Row
          label="Pipeline overhead"
          tech={`${debug.pipeline_took_ms - debug.provider_took_ms} ms`}
          plain="Time spent on query classification, alias resolution, term expansion, and re-ranking on top of Elasticsearch results."
        />

      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    background: colors.bg,
    color: colors.text,
    padding: 'clamp(16px, 4vw, 32px) clamp(12px, 4vw, 24px)',
    maxWidth: 'min(860px, 100%)',
    margin: '0 auto',
    display: 'flex',
    flexDirection: 'column',
    gap: 20,
    boxSizing: 'border-box',
  },
  topBar: {
    display: 'flex',
    alignItems: 'center',
    gap: 16,
  },
  backBtn: {
    background: 'none',
    border: `1px solid ${colors.borderSubtle}`,
    color: colors.textMuted,
    borderRadius: radius.sm,
    padding: '5px 12px',
    fontFamily: font.mono,
    fontSize: 12,
    cursor: 'pointer',
  },
  topQuery: {
    fontFamily: font.mono,
    fontSize: 12,
    color: colors.textDim,
  },
  topQueryVal: {
    color: colors.accent,
  },
  card: {
    borderRadius: radius.lg,
    overflow: 'hidden',
  },
  notFound: {
    fontFamily: font.mono,
    color: colors.textDim,
    fontSize: 14,
  },
  back: {
    color: colors.accent,
    cursor: 'pointer',
  },
  panel: {
    border: `1px solid ${colors.border}`,
    borderRadius: radius.lg,
    background: colors.surface,
    overflow: 'hidden',
  },
  sectionTitle: {
    fontFamily: font.mono,
    fontSize: 10,
    color: colors.textDim,
    textTransform: 'uppercase',
    letterSpacing: '0.1em',
    padding: '12px 18px 6px',
    background: colors.surfaceAlt,
    borderTop: `1px solid ${colors.border}`,
    borderBottom: `1px solid ${colors.border}`,
  },
  row: {
    display: 'flex',
    gap: 0,
    borderBottom: `1px solid ${colors.panel}`,
  },
  rowLabel: {
    fontFamily: font.mono,
    fontSize: 11,
    color: colors.text,
    minWidth: 160,
    flexShrink: 0,
    padding: '12px 18px',
    borderRight: `1px solid ${colors.panel}`,
    display: 'flex',
    alignItems: 'flex-start',
  },
  rowBody: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
    padding: '10px 16px',
    flex: 1,
  },
  rowTech: {
    fontFamily: font.mono,
    fontSize: 12,
    color: colors.accent,
    wordBreak: 'break-all',
  },
  rowPlain: {
    fontFamily: font.mono,
    fontSize: 12,
    color: colors.textMuted,
    lineHeight: 1.6,
  },
}
