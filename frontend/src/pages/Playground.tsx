import { useEffect, useState } from 'react'
import { useSearch } from '../hooks/useSearch'
import { useRecentSearches } from '../hooks/useRecentSearches'
import { SearchInput } from '../components/SearchInput'
import { ResultPanel } from '../components/ResultPanel'
import { colors, font } from '../theme'

interface TrendingQuery { query: string; count: number }

export function Playground() {
  const { query, submitResult, suggestionResult, loading, error, setQuery, submit } = useSearch()
  const { recents, saveRecent, removeRecent } = useRecentSearches()
  const [trending, setTrending] = useState<TrendingQuery[]>([])

  useEffect(() => {
    fetch('/api/v1/trending?limit=6')
      .then(r => r.ok ? r.json() : { queries: [] })
      .then(d => setTrending(d.queries ?? []))
      .catch(() => {})
  }, [])

  const activeResult = submitResult ?? suggestionResult

  return (
    <div style={styles.root}>
      <header style={styles.header}>
        <h1 style={styles.title}>cirro-search</h1>
        <span style={styles.subtitle}>search playground</span>
      </header>

      <SearchInput
        value={query}
        loading={loading}
        onChange={setQuery}
        onSubmit={submit}
      />

      <ResultPanel
        result={activeResult}
        error={error}
        loading={loading}
        saveRecent={saveRecent}
        recents={recents}
        trending={trending}
        onEmptySelect={submit}
        onRemoveRecent={removeRecent}
      />
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  root: {
    minHeight: '100vh',
    background: colors.bg,
    color: colors.text,
    padding: 'clamp(16px, 4vw, 32px) clamp(12px, 4vw, 24px)',
    maxWidth: 'min(900px, 100%)',
    margin: '0 auto',
    display: 'flex',
    flexDirection: 'column',
    gap: 20,
    boxSizing: 'border-box',
  },
  header: {
    display: 'flex',
    alignItems: 'baseline',
    gap: 16,
  },
  title: {
    margin: 0,
    fontSize: 22,
    fontFamily: font.mono,
    color: colors.accent,
    fontWeight: 600,
  },
  subtitle: {
    fontFamily: font.mono,
    fontSize: 12,
    color: colors.textFaint,
  },
}
