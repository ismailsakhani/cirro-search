import type { SearchResponse, SuggestionResponse } from '../types/search'

const BASE = '/api/v1'

export async function search(q: string): Promise<SearchResponse> {
  const res = await fetch(`${BASE}/search?q=${encodeURIComponent(q)}`)
  if (!res.ok) throw new Error(`Search failed: ${res.status}`)
  return res.json()
}

export async function suggestions(q: string): Promise<SuggestionResponse> {
  const res = await fetch(`${BASE}/suggestions?q=${encodeURIComponent(q)}`)
  if (!res.ok) throw new Error(`Suggestions failed: ${res.status}`)
  return res.json()
}
