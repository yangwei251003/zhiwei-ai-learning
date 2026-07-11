import axios, { AxiosError } from 'axios'

type AuthTokenProvider = () => string | null
type UnauthorizedHandler = () => void

let authTokenProvider: AuthTokenProvider = () => null
let unauthorizedHandler: UnauthorizedHandler = () => undefined

export class ApiError extends Error {
  readonly status?: number
  readonly data?: unknown

  constructor(
    message: string,
    status?: number,
    data?: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.data = data
  }
}

export function setAuthTokenProvider(provider: AuthTokenProvider): void {
  authTokenProvider = provider
}

export function setUnauthorizedHandler(handler: UnauthorizedHandler): void {
  unauthorizedHandler = handler
}

const http = axios.create({ timeout: 8000 })

http.interceptors.request.use((config) => {
  const token = authTokenProvider()
  if (token) {
    config.headers.set('Authorization', `Bearer ${token}`)
  }
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (!(error instanceof AxiosError)) {
      return Promise.reject(new ApiError('请求失败，请稍后重试'))
    }

    const status = error.response?.status
    const url = error.config?.url ?? ''
    const isAuthRequest = /\/auth\/(login|register)\/?(?:\?|$)/.test(url)

    if (status === 401) {
      if (!isAuthRequest) unauthorizedHandler()
      return Promise.reject(new ApiError('登录已过期，请重新登录', status, error.response?.data))
    }

    const responseData = error.response?.data
    const serverMessage =
      responseData && typeof responseData === 'object'
        ? Reflect.get(responseData, 'detail') ?? Reflect.get(responseData, 'message')
        : undefined
    const message =
      typeof serverMessage === 'string'
        ? serverMessage
        : status
          ? '请求失败，请稍后重试'
          : '网络连接失败，请检查网络后重试'

    return Promise.reject(new ApiError(message, status, responseData))
  },
)

export default http
