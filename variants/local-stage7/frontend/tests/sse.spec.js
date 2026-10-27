import { describe, expect, it, vi } from 'vitest'

import { createSSEParser, postChatStream } from '@/utils/sse'

describe('createSSEParser', () => {
  it('keeps partial frames across chunks and ignores heartbeat comments', () => {
    const events = []
    const parser = createSSEParser((event) => events.push(event))

    parser.push(': ping\n\ndata: {"type":"token","content":"你"}\n')
    expect(events).toEqual([])

    parser.push('\ndata: {"type":"done","conversation_id":7}\n\n')

    expect(events).toEqual([
      { type: 'token', content: '你' },
      { type: 'done', conversation_id: 7 },
    ])
  })

  it('reports malformed JSON instead of turning it into content', () => {
    const parser = createSSEParser(() => {})

    expect(() => parser.push('data: not-json\n\n')).toThrow('流式事件格式无效')
  })
})

describe('postChatStream', () => {
  it('uses POST and decodes UTF-8 events from a readable response', async () => {
    const encoder = new TextEncoder()
    const body = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"type":"token","content":"学'))
        controller.enqueue(encoder.encode('习"}\n\ndata: {"type":"done"}\n\n'))
        controller.close()
      },
    })
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => 'text/event-stream; charset=utf-8' },
      body,
    })
    const events = []

    await postChatStream({
      message: '解释状态机',
      conversationId: 3,
      token: 'jwt-token',
      onEvent: (event) => events.push(event),
      fetchImpl,
    })

    expect(fetchImpl).toHaveBeenCalledWith(
      '/api/chat/stream',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({ Authorization: 'Bearer jwt-token' }),
        body: JSON.stringify({ message: '解释状态机', conversation_id: 3 }),
      }),
    )
    expect(events).toEqual([{ type: 'token', content: '学习' }, { type: 'done' }])
  })

  it('surfaces the real upstream authorization failure without emitting success', async () => {
    const onEvent = vi.fn()
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: vi.fn().mockResolvedValue({ detail: 'AppIdNoAuthError' }),
    })

    await expect(
      postChatStream({ message: '测试', token: 'jwt-token', onEvent, fetchImpl }),
    ).rejects.toThrow('AppIdNoAuthError')
    expect(onEvent).not.toHaveBeenCalled()
  })

  it('rejects a successful response that is not an event stream', async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => 'application/json' },
      body: new ReadableStream({ start(controller) { controller.close() } }),
    })

    await expect(
      postChatStream({ message: '测试', token: 'jwt-token', onEvent: vi.fn(), fetchImpl }),
    ).rejects.toThrow('不是事件流')
  })

  it('rejects an interrupted stream that reaches EOF before done', async () => {
    const encoder = new TextEncoder()
    const onEvent = vi.fn()
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      headers: { get: () => 'text/event-stream' },
      body: new ReadableStream({
        start(controller) {
          controller.enqueue(encoder.encode('data: {"type":"token","content":"半"}\n\n'))
          controller.close()
        },
      }),
    })

    await expect(
      postChatStream({ message: '测试', token: 'jwt-token', onEvent, fetchImpl }),
    ).rejects.toThrow('完成前中断')
    expect(onEvent).toHaveBeenCalledWith({ type: 'token', content: '半' })
  })
})
