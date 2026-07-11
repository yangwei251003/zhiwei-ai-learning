import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useUserStore } from '../stores/user'
import { setAuthTokenProvider, setUnauthorizedHandler } from '../utils/http'
import { createAppRouter, installAuthGuard } from './index'

vi.mock('../utils/http', () => ({
  default: { get: vi.fn(), patch: vi.fn(), post: vi.fn() },
  setAuthTokenProvider: vi.fn(),
  setUnauthorizedHandler: vi.fn(),
}))

const storage = new Map<string, string>()

describe('authentication route guard', () => {
  beforeEach(() => {
    storage.clear()
    vi.resetAllMocks()
    vi.stubGlobal('localStorage', {
      getItem: (key: string) => storage.get(key) ?? null,
      removeItem: (key: string) => storage.delete(key),
      setItem: (key: string, value: string) => storage.set(key, value),
    })
  })

  function setup() {
    const pinia = createPinia()
    setActivePinia(pinia)
    const router = createAppRouter()
    installAuthGuard(router, pinia)
    return { router, store: useUserStore(pinia) }
  }

  it('binds the HTTP authentication client when the guard is installed', () => {
    const { store } = setup()
    store.token = 'router-bound-token'

    const provider = vi.mocked(setAuthTokenProvider).mock.calls[0]?.[0]
    const unauthorized = vi.mocked(setUnauthorizedHandler).mock.calls[0]?.[0]
    expect(provider?.()).toBe('router-bound-token')
    unauthorized?.()
    expect(store.token).toBeNull()
  })

  it('restores the session before the first navigation and redirects a guest with fullPath', async () => {
    const { router, store } = setup()
    const restore = vi.spyOn(store, 'restoreSession')

    await router.push('/workbench?tab=plan')

    expect(restore).toHaveBeenCalledOnce()
    expect(router.currentRoute.value.fullPath).toBe('/login?redirect=/workbench?tab=plan')
  })

  it('allows an authenticated user to enter the workbench without restoring twice', async () => {
    const { router, store } = setup()
    store.token = 'valid-token'
    store.user = { id: 1, username: 'student', email: 'student@example.com', learning_style: 'visual' }
    store.sessionRestored = true
    const restore = vi.spyOn(store, 'restoreSession')

    await router.push('/workbench')

    expect(router.currentRoute.value.path).toBe('/workbench')
    expect(restore).not.toHaveBeenCalled()
  })

  it.each(['/login', '/register'])('redirects an authenticated user from %s to the workbench', async (path) => {
    const { router, store } = setup()
    store.token = 'valid-token'
    store.user = { id: 1, username: 'student', email: 'student@example.com', learning_style: 'visual' }
    store.sessionRestored = true

    await router.push(path)

    expect(router.currentRoute.value.path).toBe('/workbench')
  })

  it.each([
    [false, '/login'],
    [true, '/workbench'],
  ])('routes the root according to authentication state', async (authenticated, expected) => {
    const { router, store } = setup()
    if (authenticated) {
      store.token = 'valid-token'
      store.user = { id: 1, username: 'student', email: 'student@example.com', learning_style: 'visual' }
      store.sessionRestored = true
    }

    await router.push('/')

    expect(router.currentRoute.value.path).toBe(expected)
  })
})
