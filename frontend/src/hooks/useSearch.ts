import { useCallback, useEffect, useRef, useState } from 'react'
import { search, suggestions } from '../api/searchClient'
import type { SearchResponse, SuggestionResponse } from '../types/search'

interface SearchState {
  query: string
  submitResult: SearchResponse | null
  suggestionResult: SuggestionResponse | null
  loading: boolean
  error: string | null
}

export function useSearch() {
  const [state, setState] = useState<SearchState>({
    query: '',
    submitResult: null,
    suggestionResult: null,
    loading: false,
    error: null,
  })

  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Ref kept in sync with state — lets submit() read current suggestions
  // without a stale closure (submit has [] deps so captures no state).
  const suggestionResultRef = useRef<SuggestionResponse | null>(null)
  useEffect(() => {
    suggestionResultRef.current = state.suggestionResult
  }, [state.suggestionResult])

  const setQuery = useCallback((q: string) => {
    setState(prev => ({ ...prev, query: q, error: null }))

    if (debounceTimer.current) clearTimeout(debounceTimer.current)

    if (!q.trim()) {
      setState(prev => ({ ...prev, suggestionResult: null }))
      return
    }

    debounceTimer.current = setTimeout(async () => {
      setState(prev => ({ ...prev, loading: true }))
      try {
        const result = await suggestions(q)
        setState(prev => ({ ...prev, suggestionResult: result, loading: false }))
      } catch (e) {
        setState(prev => ({
          ...prev,
          error: e instanceof Error ? e.message : 'Suggestion failed',
          loading: false,
        }))
      }
    }, 200)
  }, [])

  const submit = useCallback(async (q: string) => {
    if (!q.trim()) return
    if (debounceTimer.current) clearTimeout(debounceTimer.current)

    // Normalize: lowercase + strip spaces for comparison
    const normalizedQ = q.trim().toLowerCase().replace(/\s+/g, '')

    // Step 1 — check current suggestion results before hitting ES.
    // Common case: user sees EWR in the suggestion list, presses Enter.
    // Exact match on iata / icao / iata_flight / gate avoids a round-trip.
    const currentSuggestions = suggestionResultRef.current
    if (currentSuggestions?.results.length) {
      const hit = currentSuggestions.results.find(r =>
        r.iata?.toLowerCase() === normalizedQ ||
        r.icao?.toLowerCase() === normalizedQ ||
        r.iata_flight?.toLowerCase().replace(/\s+/g, '') === normalizedQ ||
        r.gate?.toLowerCase() === normalizedQ
      )
      if (hit) {
        setState(prev => ({
          ...prev,
          query: q,
          submitResult: { ...currentSuggestions, results: [hit], mode: 'submit' },
          suggestionResult: null,
          loading: false,
          error: null,
        }))
        return
      }
    }

    // Step 2 — no local match, fall through to ES.
    setState(prev => ({ ...prev, query: q, loading: true, error: null }))
    try {
      const result = await search(q)
      setState(prev => ({ ...prev, submitResult: result, suggestionResult: null, loading: false }))
    } catch (e) {
      setState(prev => ({
        ...prev,
        error: e instanceof Error ? e.message : 'Search failed',
        loading: false,
      }))
    }
  }, [])

  const selectSuggestion = useCallback(async (q: string) => {
    if (debounceTimer.current) clearTimeout(debounceTimer.current)
    setState(prev => ({ ...prev, query: q, loading: true, error: null }))
    try {
      const result = await search(q)
      setState(prev => ({ ...prev, submitResult: result, suggestionResult: null, loading: false }))
    } catch (e) {
      setState(prev => ({
        ...prev,
        error: e instanceof Error ? e.message : 'Search failed',
        loading: false,
      }))
    }
  }, [])

  useEffect(() => {
    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current)
    }
  }, [])

  return { ...state, setQuery, submit, selectSuggestion }
}
