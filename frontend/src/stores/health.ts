import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import http from '../utils/http'

type HealthPayload = { status: string; llm: string }

export const useHealthStore = defineStore('health', () => {
  const loading = ref(false)
  const payload = ref<HealthPayload | null>(null)
  const error = ref('')
  const status = ref<'idle' | 'online' | 'offline'>('idle')
  const label = computed(() => ({ idle: '等待检查', online: '服务在线', offline: '连接失败' })[status.value])
  async function check() {
    loading.value = true
    error.value = ''
    try {
      const response = await http.get<HealthPayload>('/api/health')
      payload.value = response.data
      status.value = 'online'
    } catch (cause) {
      payload.value = null
      status.value = 'offline'
      error.value = cause instanceof Error ? cause.message : '无法连接后端服务'
    } finally { loading.value = false }
  }
  return { check, error, label, loading, payload, status }
})
