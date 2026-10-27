import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import http from '../utils/http'
import { useHealthStore } from './health'

vi.mock('../utils/http', () => ({ default: { get: vi.fn() } }))

describe('health store', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('checks the backend health endpoint exposed by the development proxy', async () => {
    vi.mocked(http.get).mockResolvedValue({ data: { status: 'ok', llm: 'ready' } })
    const store = useHealthStore()
    await store.check()
    expect(http.get).toHaveBeenCalledWith('/api/health')
    expect(store.status).toBe('online')
  })
})
