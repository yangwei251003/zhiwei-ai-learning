import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { apiClient } from '@/api/request'
import { useChatStore } from '@/stores/chat'


describe('chat history store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('loads real history summaries and selects ordered persisted messages', async () => {
    vi.spyOn(apiClient, 'get')
      .mockResolvedValueOnce([
        {
          id: 7,
          title: '递归复习',
          message_count: 2,
          last_message: '递归是函数调用自身',
        },
      ])
      .mockResolvedValueOnce({
        id: 7,
        title: '递归复习',
        messages: [
          { id: 11, role: 'user', content: '什么是递归？' },
          { id: 12, role: 'assistant', content: '递归是函数调用自身' },
        ],
      })
    const store = useChatStore()

    await store.loadHistory()
    await store.selectConversation(7)

    expect(store.history).toHaveLength(1)
    expect(store.conversationId).toBe(7)
    expect(store.messages).toEqual([
      { id: 11, role: 'user', content: '什么是递归？', status: 'done' },
      { id: 12, role: 'assistant', content: '递归是函数调用自身', status: 'done' },
    ])
  })

  it('keeps history errors separate from generation errors', async () => {
    vi.spyOn(apiClient, 'get').mockRejectedValueOnce(new Error('历史服务不可用'))
    const store = useChatStore()

    await store.loadHistory()

    expect(store.history).toEqual([])
    expect(store.historyError).toBe('历史服务不可用')
    expect(store.error).toBe('')
  })
})
