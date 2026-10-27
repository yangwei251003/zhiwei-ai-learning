import axios from 'axios'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 20000,
  headers: { Accept: 'application/json' },
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('xzxx-token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

apiClient.interceptors.response.use(
  (response) => response.data?.data ?? response.data,
  (error) => {
    const message = error.response?.data?.detail || error.response?.data?.message || error.message
    return Promise.reject(new Error(message || '网络请求失败'))
  },
)
