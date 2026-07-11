import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import http, { ApiError, setAuthTokenProvider, setUnauthorizedHandler } from '../utils/http'
import { bindUserStoreToHttp, useUserStore } from './user'

vi.mock('../utils/http', () => ({
  ApiError: class ApiError extends Error {
    readonly status?: number
    constructor(message: string, status?: number) {
      super(message)
      this.status = status
    }
  },
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
    vi.resetAllMocks()
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
    vi.mocked(http.get).mockRejectedValueOnce(new ApiError('unauthorized', 401))

    const store = useUserStore()
    await store.restoreSession()
    await store.restoreSession()

    expect(http.get).toHaveBeenCalledTimes(1)
    expect(store.token).toBeNull()
    expect(store.user).toBeNull()
    expect(store.sessionRestored).toBe(true)
    expect(localStorage.getItem('zhiwei.auth.token')).toBeNull()
  })

  it('uses memory state when persistent storage is unavailable', async () => {
    vi.stubGlobal('localStorage', {
      getItem: () => { throw new DOMException('blocked', 'SecurityError') },
      removeItem: () => { throw new DOMException('blocked', 'SecurityError') },
      setItem: () => { throw new DOMException('blocked', 'SecurityError') },
    })
    vi.mocked(http.post).mockResolvedValueOnce({ data: { access_token: 'memory-token' } })
    vi.mocked(http.get).mockResolvedValueOnce({
      data: { id: 1, username: 'student', email: 'a@b.com', learning_style: 'visual' },
    })
    const store = useUserStore()

    await expect(store.login({ username: 'student', password: 'secret' })).resolves.toBeUndefined()
    await expect(store.restoreSession()).resolves.toBeUndefined()

    expect(store.token).toBe('memory-token')
  })

  it('cleans up and rethrows when login cannot load the current user', async () => {
    const failure = new Error('me unavailable')
    vi.mocked(http.post).mockResolvedValueOnce({ data: { access_token: 'orphan-token' } })
    vi.mocked(http.get).mockRejectedValueOnce(failure)
    const store = useUserStore()

    await expect(store.login({ username: 'student', password: 'secret' })).rejects.toBe(failure)

    expect(store.token).toBeNull()
    expect(store.user).toBeNull()
    expect(localStorage.getItem('zhiwei.auth.token')).toBeNull()
  })

  it('returns partial success when registration cannot load the current user', async () => {
    vi.mocked(http.post).mockResolvedValueOnce({ data: { access_token: 'created-token' } })
    vi.mocked(http.get).mockRejectedValueOnce(new Error('me unavailable'))
    const store = useUserStore()

    const result = await store.register({
      username: 'created', password: 'secret', email: 'created@example.com', learning_style: 'visual',
      major: '软件工程', cognitive_style: '视觉型',
    })

    expect(result).toEqual({ profileSaved: false })
    expect(store.token).toBe('created-token')
    expect(store.user).toBeNull()
    expect(http.patch).not.toHaveBeenCalled()
  })

  it('keeps the persisted token after a temporary restore failure', async () => {
    localStorage.setItem('zhiwei.auth.token', 'retry-token')
    vi.mocked(http.get).mockRejectedValueOnce(new ApiError('server unavailable', 503))
    const store = useUserStore()

    await expect(store.restoreSession()).resolves.toBeUndefined()

    expect(store.token).toBe('retry-token')
    expect(store.sessionRestored).toBe(true)
    expect(localStorage.getItem('zhiwei.auth.token')).toBe('retry-token')
  })

  it('does not let a late restore response authenticate after logout', async () => {
    localStorage.setItem('zhiwei.auth.token', 'old-token')
    let resolveMe!: (value: { data: { id: number; username: string; email: string; learning_style: 'visual' } }) => void
    vi.mocked(http.get).mockReturnValueOnce(new Promise((resolve) => { resolveMe = resolve }))
    const store = useUserStore()

    const restoring = store.restoreSession()
    store.logout()
    resolveMe({ data: { id: 1, username: 'old', email: 'old@example.com', learning_style: 'visual' } })
    await restoring

    expect(store.token).toBeNull()
    expect(store.user).toBeNull()
  })

  it('binds HTTP authentication callbacks to the requested store', () => {
    const store = useUserStore()
    store.token = 'bound-token'

    bindUserStoreToHttp(store)

    const provider = vi.mocked(setAuthTokenProvider).mock.calls[0][0]
    const unauthorized = vi.mocked(setUnauthorizedHandler).mock.calls[0][0]
    expect(provider()).toBe('bound-token')
    unauthorized()
    expect(store.token).toBeNull()
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
