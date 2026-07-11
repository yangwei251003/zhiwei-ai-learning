import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import http from '../utils/http'
import { useUserStore } from './user'

vi.mock('../utils/http', () => ({
  default: {
    get: vi.fn(),
    patch: vi.fn(),
    post: vi.fn(),
  },
  setAuthTokenProvider: vi.fn(),
  setUnauthorizedHandler: vi.fn(),
}))

const storage = new Map<string, string>()

describe('user store', () => {
  beforeEach(() => {
    storage.clear()
    vi.clearAllMocks()
    vi.stubGlobal('localStorage', {
      getItem: (key: string) => storage.get(key) ?? null,
      removeItem: (key: string) => storage.delete(key),
      setItem: (key: string, value: string) => storage.set(key, value),
    })
    setActivePinia(createPinia())
  })

  it('login saves the access token and current user', async () => {
    const user = { id: 1, username: 'student', email: 'student@example.com', learning_style: 'visual' as const }
    vi.mocked(http.post).mockResolvedValueOnce({ data: { access_token: 'token-1', token_type: 'bearer' } })
    vi.mocked(http.get).mockResolvedValueOnce({ data: user })

    const store = useUserStore()
    await store.login({ username: 'student', password: 'secret' })

    expect(http.post).toHaveBeenCalledWith('/api/auth/login', { username: 'student', password: 'secret' })
    expect(http.get).toHaveBeenCalledWith('/api/auth/me')
    expect(store.token).toBe('token-1')
    expect(store.user).toEqual(user)
    expect(store.isAuthenticated).toBe(true)
    expect(localStorage.getItem('zhiwei.auth.token')).toBe('token-1')
  })

  it('restoreSession clears an invalid persisted token', async () => {
    localStorage.setItem('zhiwei.auth.token', 'expired')
    vi.mocked(http.get).mockRejectedValueOnce(new Error('unauthorized'))

    const store = useUserStore()
    await store.restoreSession()
    await store.restoreSession()

    expect(http.get).toHaveBeenCalledTimes(1)
    expect(store.token).toBeNull()
    expect(store.user).toBeNull()
    expect(store.sessionRestored).toBe(true)
    expect(localStorage.getItem('zhiwei.auth.token')).toBeNull()
  })

  it('restoreSession shares one in-flight restoration', async () => {
    localStorage.setItem('zhiwei.auth.token', 'valid')
    vi.mocked(http.get).mockResolvedValue({
      data: { id: 1, username: 'student', email: 'student@example.com', learning_style: 'visual' },
    })
    const store = useUserStore()

    await Promise.all([store.restoreSession(), store.restoreSession()])

    expect(http.get).toHaveBeenCalledOnce()
  })

  it('register keeps the valid account when profile saving fails', async () => {
    const user = { id: 2, username: 'new-user', email: 'new@example.com', learning_style: 'hands_on' as const }
    vi.mocked(http.post).mockResolvedValueOnce({ data: { access_token: 'token-2', token_type: 'bearer' } })
    vi.mocked(http.get).mockResolvedValueOnce({ data: user })
    vi.mocked(http.patch).mockRejectedValueOnce(new Error('profile unavailable'))

    const store = useUserStore()
    const result = await store.register({
      username: 'new-user',
      password: 'secret',
      email: 'new@example.com',
      learning_style: 'hands_on',
      major: '软件工程',
      cognitive_style: '实践型',
    })

    expect(http.post).toHaveBeenCalledWith('/api/auth/register', {
      username: 'new-user', password: 'secret', email: 'new@example.com', learning_style: 'hands_on',
    })
    expect(http.patch).toHaveBeenCalledWith('/api/profile/current', {
      major: '软件工程', cognitive_style: '实践型',
    })
    expect(result).toEqual({ profileSaved: false })
    expect(store.token).toBe('token-2')
    expect(store.user).toEqual(user)
  })

  it('saveProfile omits an absent learning style', async () => {
    vi.mocked(http.patch).mockResolvedValue({ data: {} })
    const store = useUserStore()

    await store.saveProfile('计算机科学')
    await store.saveProfile('软件工程', 'visual')

    expect(http.patch).toHaveBeenNthCalledWith(1, '/api/profile/current', { major: '计算机科学' })
    expect(http.patch).toHaveBeenNthCalledWith(2, '/api/profile/current', {
      major: '软件工程', cognitive_style: 'visual',
    })
  })

  it('logout clears authentication state and persistent storage', async () => {
    vi.mocked(http.post).mockResolvedValueOnce({ data: { access_token: 'token-3', token_type: 'bearer' } })
    vi.mocked(http.get).mockResolvedValueOnce({ data: { id: 3, username: 'student', email: 'a@b.com', learning_style: 'visual' } })
    const store = useUserStore()
    await store.login({ username: 'student', password: 'secret' })

    store.logout()

    expect(store.token).toBeNull()
    expect(store.user).toBeNull()
    expect(store.isAuthenticated).toBe(false)
    expect(localStorage.getItem('zhiwei.auth.token')).toBeNull()
  })
})
