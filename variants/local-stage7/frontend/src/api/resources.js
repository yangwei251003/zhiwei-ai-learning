import { apiClient } from './request'

export const listResources = (params = {}) => apiClient.get('/resources/', { params })
export const getResource = (id) => apiClient.get(`/resources/${id}`)
