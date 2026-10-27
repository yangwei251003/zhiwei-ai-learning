function parseFrame(frame, onEvent) {
  const data = frame
    .split(/\r?\n/)
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trimStart())
    .join('\n')

  if (!data) return

  try {
    onEvent(JSON.parse(data))
  } catch (error) {
    throw new Error('流式事件格式无效', { cause: error })
  }
}

export function createSSEParser(onEvent) {
  let buffer = ''

  return {
    push(chunk) {
      buffer += chunk.replaceAll('\r\n', '\n')
      let boundary = buffer.indexOf('\n\n')
      while (boundary >= 0) {
        const frame = buffer.slice(0, boundary)
        buffer = buffer.slice(boundary + 2)
        parseFrame(frame, onEvent)
        boundary = buffer.indexOf('\n\n')
      }
    },
    finish() {
      if (buffer.trim()) parseFrame(buffer, onEvent)
      buffer = ''
    },
  }
}

async function responseError(response) {
  try {
    const payload = await response.json()
    return payload.detail || payload.message || `请求失败 (${response.status})`
  } catch {
    return `请求失败 (${response.status})`
  }
}

export async function postChatStream({
  message,
  conversationId,
  token,
  onEvent,
  signal,
  fetchImpl = fetch,
}) {
  const response = await fetchImpl('/api/chat/stream', {
    method: 'POST',
    headers: {
      Accept: 'text/event-stream',
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      message,
      ...(conversationId ? { conversation_id: conversationId } : {}),
    }),
    signal,
  })

  if (!response.ok) throw new Error(await responseError(response))
  const contentType = response.headers?.get?.('content-type') || ''
  if (!contentType.toLowerCase().startsWith('text/event-stream')) {
    throw new Error('服务响应不是事件流')
  }
  if (!response.body) throw new Error('浏览器未提供可读取的流式响应')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let receivedDone = false
  const parser = createSSEParser((event) => {
    if (event.type === 'done') receivedDone = true
    onEvent(event)
  })

  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      parser.push(decoder.decode(value, { stream: true }))
    }
    parser.push(decoder.decode())
    parser.finish()
    if (!receivedDone) throw new Error('流式响应在完成前中断')
  } finally {
    reader.releaseLock()
  }
}
