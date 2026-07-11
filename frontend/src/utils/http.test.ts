import { AxiosError, type AxiosAdapter, type AxiosResponse } from 'axios'
import { afterEach, describe, expect, it, vi } from 'vitest'

import http, { setAuthTokenProvider, setUnauthorizedHandler } from './http'

describe('authenticated HTTP client', () => {
  afterEach(() => {
    setAuthTokenProvider(() => null)
    setUnauthorizedHandler(() => undefined)
  })

  it('adds the bearer token supplied by the auth token provider', async () => {
    let authorization: unknown
    const adapter: AxiosAdapter = async (config) => {
      authorization = config.headers.get('Authorization')
      return {
        data: {},
        status: 200,
        statusText: 'OK',
        headers: {},
        config,
      }
    }

    setAuthTokenProvider(() => 'token-value')
    await http.get('/api/profile', { adapter })

    expect(authorization).toBe('Bearer token-value')
  })

  it('handles unauthorized responses and throws a localized API error', async () => {
    const unauthorizedHandler = vi.fn()
    const adapter: AxiosAdapter = async (config) => {
      const response: AxiosResponse = {
        data: {},
        status: 401,
        statusText: 'Unauthorized',
        headers: {},
        config,
      }
      throw new AxiosError('Request failed', 'ERR_BAD_REQUEST', config, undefined, response)
    }

    setUnauthorizedHandler(unauthorizedHandler)

    await expect(http.get('/api/profile', { adapter })).rejects.toMatchObject({
      message: '登录已过期，请重新登录',
    })
    expect(unauthorizedHandler).toHaveBeenCalledOnce()
  })
})
