import { createMemoryHistory } from 'vue-router'
import { describe, expect, it } from 'vitest'

import { createAppRouter, routes } from '@/router'

describe('application router', () => {
  it('declares the eight product routes', () => {
    expect(routes.map((route) => route.path)).toEqual([
      '/login',
      '/register',
      '/',
      '/chat',
      '/resources',
      '/path',
      '/tutor',
      '/admin',
    ])
  })

  it('redirects unauthenticated users away from protected routes', async () => {
    const router = createAppRouter(createMemoryHistory(), () => false)

    await router.push('/chat')
    await router.isReady()

    expect(router.currentRoute.value.path).toBe('/login')
    expect(router.currentRoute.value.query.redirect).toBe('/chat')
  })
})
