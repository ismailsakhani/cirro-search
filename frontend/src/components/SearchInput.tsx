import { KeyboardEvent, useState } from 'react'
import { useCyclingPlaceholder } from '../hooks/useCyclingPlaceholder'
import { colors, font, radius } from '../theme'

const PLACEHOLDERS = [
  'Search for an airport — try EWR or heathrow',
  'Search for a flight — try UA44 or ba117',
  'Search for a gate — try C101 or B7',
  'Try a city name — try dubai or hong kong',
]

interface Props {
  value: string
  loading: boolean
  onChange: (v: string) => void
  onSubmit: (v: string) => void
}

export function SearchInput({ value, loading, onChange, onSubmit }: Props) {
  const [focused, setFocused] = useState(false)
  const [btnHover, setBtnHover] = useState(false)
  const placeholder = useCyclingPlaceholder(PLACEHOLDERS, 3000)

  function handleKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') onSubmit(value)
    if (e.key === 'Escape') onChange('')
  }

  return (
    <div style={styles.wrapper}>
      <input
        style={{
          ...styles.input,
          border: focused ? `1px solid ${colors.accentActive}` : `1px solid ${colors.borderSubtle}`,
        }}
        type="text"
        value={value}
        placeholder={placeholder}
        onChange={e => onChange(e.target.value)}
        onKeyDown={handleKey}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        autoFocus
        spellCheck={false}
        autoComplete="off"
      />
      <button
        style={{
          ...styles.btn,
          background: loading ? colors.accentDisabled : btnHover ? colors.accentHover : colors.accentActive,
          cursor: loading ? 'not-allowed' : 'pointer',
          opacity: loading ? 0.75 : 1,
        }}
        onClick={() => onSubmit(value)}
        disabled={loading}
        onMouseEnter={() => setBtnHover(true)}
        onMouseLeave={() => setBtnHover(false)}
      >
        {loading ? '…' : 'Search'}
      </button>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    display: 'flex',
    gap: 8,
    position: 'relative',
  },
  input: {
    flex: 1,
    padding: '10px 14px',
    fontSize: 16,
    fontFamily: font.mono,
    background: colors.panel,
    borderRadius: radius.md,
    color: colors.text,
    outline: 'none',
    transition: 'border-color 0.15s',
    minWidth: 0,
  },
  btn: {
    padding: '10px 20px',
    fontSize: 14,
    color: '#fff',
    border: 'none',
    borderRadius: radius.md,
    fontFamily: font.mono,
    flexShrink: 0,
    transition: 'background 0.15s, opacity 0.15s',
  },
}
