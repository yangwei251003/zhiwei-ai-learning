import { beforeEach, describe, expect, it, vi } from 'vitest'

import { generatePath } from '@/api/path'
import { apiClient } from '@/api/request'
import { uploadKnowledge } from '@/api/system'


describe('long-running real backend requests', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('gives Spark path generation enough time without changing the global timeout', async () => {
    const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ id: 1 })

    await generatePath('两周内掌握图遍历')

    expect(post).toHaveBeenCalledWith(
      '/path/generate',
      { goal: '两周内掌握图遍历' },
      { timeout: 180_000 },
    )
    expect(apiClient.defaults.timeout).toBe(20_000)
  })

  it('gives document parsing and embedding enough time', async () => {
    const post = vi.spyOn(apiClient, 'post').mockResolvedValue({ id: 1 })
    const file = new File(['课程内容'], 'lesson.txt', { type: 'text/plain' })

    await uploadKnowledge(file)

    expect(post).toHaveBeenCalledWith(
      '/knowledge/upload',
      expect.any(FormData),
      { timeout: 180_000 },
    )
  })
})
