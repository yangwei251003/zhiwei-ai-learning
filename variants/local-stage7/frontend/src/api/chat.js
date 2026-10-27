import { apiClient } from './request'


export const listConversations = () => apiClient.get('/chat/conversations')
export const getConversation = (id) => apiClient.get(`/chat/conversations/${id}`)
