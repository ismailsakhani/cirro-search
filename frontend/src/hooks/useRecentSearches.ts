import { useState } from 'react'
import type { SearchResult } from '../types/search'

export interface RecentSearch {
  id: string
  display: string
  type: 'airport' | 'flight' | 'gate' | string
  iata: string | null
  icao: string | null
  iata_flight: string | null
  gate: string | null
  query: string
  savedAt: number
}

const MAX_RECENTS = 10
const STORAGE_KEY = 'cirro_recent_searches'

function readFromStorage(): RecentSearch[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function writeToStorage(items: RecentSearch[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
  } catch {
    // storage full or private browsing — degrade silently
  }
}

export function useRecentSearches() {
  const [recents, setRecents] = useState<RecentSearch[]>(() => readFromStorage())

  function saveRecent(result: SearchResult, query: string): void {
    if (!result.id) return
    const entry: RecentSearch = {
      id: result.id,
      display: result.display,
      type: result.type,
      iata: result.iata,
      icao: result.icao,
      iata_flight: result.iata_flight,
      gate: result.gate,
      query,
      savedAt: Date.now(),
    }
    setRecents(prev => {
      const deduped = prev.filter(r => r.id !== entry.id)
      const next = [entry, ...deduped].slice(0, MAX_RECENTS)
      writeToStorage(next)
      return next
    })
  }

  function removeRecent(id: string): void {
    setRecents(prev => {
      const next = prev.filter(r => r.id !== id)
      writeToStorage(next)
      return next
    })
  }

  function clearAll(): void {
    try { localStorage.removeItem(STORAGE_KEY) } catch {}
    setRecents([])
  }

  return { recents, saveRecent, removeRecent, clearAll }
}
