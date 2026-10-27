import { apiClient } from './request'

export const getAgentStatus = () => apiClient.get('/agents/status')
export const getAchievements = () => apiClient.get('/achievements/')
export const listKnowledge = () => apiClient.get('/knowledge/')
export const uploadKnowledge = (file) => {
  const data = new FormData()
  data.append('file', file)
  return apiClient.post('/knowledge/upload', data, { timeout: 180_000 })
}
export const deleteKnowledge = (id) => apiClient.delete(`/knowledge/${id}`)
export const listUsers = () => apiClient.get('/admin/users')
export const getSettings = () => apiClient.get('/admin/settings')
export const updateSettings = (settings) => apiClient.patch('/admin/settings', { settings })
