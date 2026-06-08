export interface SearchResult {
  id: string
  display: string
  type: 'airport' | 'flight' | 'gate' | string
  score: number
  iata: string | null
  icao: string | null
  name: string | null
  city: string | null
  country: string | null
  airline: string | null
  airline_name: string | null
  iata_flight: string | null
  icao_flight: string | null
  flight_number: string | null
  airport_code: string | null
  gate: string | null
  matched_fields: string[]
  explanation: string[]
  metadata: Record<string, unknown>
}

export interface DebugInfo {
  classification: {
    query_type: string
    normalized_query: string
    matched_pattern: string
    entity_type: string | null
  }
  expansions: string[]
  alias_resolution?: {
    matched: boolean
    entity_id: string | null
    entity_type: string | null
  } | null
  provider: string
  provider_took_ms: number
  pipeline_took_ms: number
  fallback_used: boolean
}

export interface SearchResponse {
  query: string
  mode: string
  results: SearchResult[]
  debug: DebugInfo
}

export type SuggestionResponse = SearchResponse
