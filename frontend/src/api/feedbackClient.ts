const BASE = '/api/v1'

export function recordSelection(resultId: string): void {
  // Fire-and-forget — never await, never block navigation.
  // Errors swallowed: tracking must never affect UX.
  fetch(`${BASE}/feedback/select`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ result_id: resultId }),
  }).catch(() => {})
}
