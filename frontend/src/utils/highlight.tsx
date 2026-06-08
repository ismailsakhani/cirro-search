import React from 'react'
import { colors } from '../theme'

/**
 * Returns the text with the first occurrence of query highlighted.
 * Uses indexOf (not regex) — safe for arbitrary user input including special chars.
 */
export function highlightMatch(text: string, query: string | undefined): React.ReactNode {
  if (!query?.trim() || !text) return text

  const q = query.trim().toLowerCase()
  const idx = text.toLowerCase().indexOf(q)

  if (idx === -1) return text

  return (
    <>
      {text.slice(0, idx)}
      <mark style={{ background: 'transparent', color: colors.accent, fontWeight: 700 }}>
        {text.slice(idx, idx + q.length)}
      </mark>
      {text.slice(idx + q.length)}
    </>
  )
}
