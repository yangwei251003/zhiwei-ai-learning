export interface SseEvent {
  type: string
  payload: Record<string, unknown>
}

export function parseSseBlock(block: string): SseEvent | null {
  const lines = block.split(/\r?\n/)
  const data = lines
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trimStart())
    .join('\n')
  if (!data) return null
  try {
    const parsed = JSON.parse(data) as Partial<SseEvent>
    if (typeof parsed.type !== 'string' || !parsed.payload || typeof parsed.payload !== 'object') return null
    return { type: parsed.type, payload: parsed.payload as Record<string, unknown> }
  } catch {
    return null
  }
}
