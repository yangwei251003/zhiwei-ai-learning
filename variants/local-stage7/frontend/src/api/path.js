import { apiClient } from './request'

export const generatePath = (goal) =>
  apiClient.post('/path/generate', { goal }, { timeout: 180_000 })
export const getPath = (id) => apiClient.get(`/path/${id}`)
export const updatePathProgress = (pathId, stepId, progress) =>
  apiClient.patch(`/path/${pathId}/progress`, { step_id: stepId, progress })
