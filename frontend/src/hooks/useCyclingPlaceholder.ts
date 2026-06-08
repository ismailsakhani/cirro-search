import { useEffect, useState } from 'react'

export function useCyclingPlaceholder(options: string[], intervalMs: number): string {
  const [index, setIndex] = useState(0)

  useEffect(() => {
    if (options.length <= 1) return
    const id = setInterval(() => {
      setIndex(i => (i + 1) % options.length)
    }, intervalMs)
    return () => clearInterval(id)
  }, [options.length, intervalMs])

  return options[index] ?? ''
}
