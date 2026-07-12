import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import http, { ApiError } from '../utils/http'
import { usePathStore } from './path'

vi.mock('../utils/http', () => ({
  ApiError: class ApiError extends Error { status?: number; constructor(message: string, status?: number) { super(message); this.status = status } },
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn() },
}))

const path = { id: 7, current_step: 1, is_active: true, path_data: [{ step: 1, topic: '基础', description: '建立概念', estimated_minutes: 20, resource_types_needed: ['document'], status: 'pending' }] }

describe('path store', () => {
  beforeEach(() => { setActivePinia(createPinia()); vi.clearAllMocks() })
  it('treats a current-path 404 as an honest empty state', async () => {
    vi.mocked(http.get).mockRejectedValue(new ApiError('not found', 404))
    const store = usePathStore(); await store.load()
    expect(http.get).toHaveBeenCalledWith('/api/path/current')
    expect(store.path).toBeNull(); expect(store.error).toBe('')
  })
  it('generates and updates a step using the path contract', async () => {
    vi.mocked(http.post).mockResolvedValue({ data: path }); vi.mocked(http.patch).mockResolvedValue({ data: { ...path, path_data: [{ ...path.path_data[0], status: 'completed' }] } })
    const store = usePathStore(); await store.generate({ message: '学会 Python', course: 'Python' }); await store.updateStep(1, 'completed')
    expect(http.post).toHaveBeenCalledWith('/api/path/generate', { message: '学会 Python', course: 'Python' }, { timeout: 60000 })
    expect(http.patch).toHaveBeenCalledWith('/api/path/7/progress', { step: 1, status: 'completed' })
    expect(store.progress).toBe(100)
  })
})
