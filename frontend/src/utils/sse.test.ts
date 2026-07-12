import { describe, expect, it } from 'vitest'

import { parseSseBlock } from './sse'

describe('SSE parser', () => {
  it('parses typed JSON events from a complete block', () => {
    expect(parseSseBlock('event: token\ndata: {"type":"token","payload":{"content":"你"}}')).toEqual({
      type: 'token',
      payload: { content: '你' },
    })
  })

  it('ignores comments and malformed blocks', () => {
    expect(parseSseBlock(': keep-alive')).toBeNull()
    expect(parseSseBlock('event: token\ndata: not-json')).toBeNull()
  })
})
