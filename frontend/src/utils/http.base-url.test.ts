import { describe, expect, it, vi } from 'vitest'

describe('HTTP client deployment configuration', () => {
  it('uses the configured public API base URL', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.zhiwei.example/')
    vi.resetModules()
    const { default: http } = await import('./http')

    expect(http.defaults.baseURL).toBe('https://api.zhiwei.example')
  })

  it('resolves streaming endpoints against the configured API origin', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.zhiwei.example/')
    vi.resetModules()
    const { resolveApiUrl } = await import('./http')

    expect(resolveApiUrl('/api/chat/stream')).toBe(
      'https://api.zhiwei.example/api/chat/stream',
    )
  })
})
