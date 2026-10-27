import { apiClient } from './request'

export const login = (payload) => apiClient.post('/auth/login', payload)
export const register = (payload) => apiClient.post('/auth/register', payload)
export const getMe = () => apiClient.get('/auth/me')
