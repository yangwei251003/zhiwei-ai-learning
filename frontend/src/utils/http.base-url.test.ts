import { describe, expect, it, vi } from 'vitest'

describe('HTTP client deployment configuration', () => {
  it('uses the configured public API base URL', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.zhiwei.example/')
    vi.resetModules()
    const { default: http } = await import('./http')

    expect(http.defaults.baseURL).toBe('https://api.zhiwei.example')
  })
})
