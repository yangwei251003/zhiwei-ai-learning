import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import type { GeneratePathInput, LearningPath, PathStepStatus } from '../types/path'
import http, { ApiError } from '../utils/http'

export const usePathStore = defineStore('path', () => {
  const path = ref<LearningPath | null>(null)
  const loading = ref(false); const generating = ref(false); const updatingStep = ref<number | null>(null); const error = ref('')
  const completedCount = computed(() => path.value?.path_data.filter((step) => step.status === 'completed').length ?? 0)
  const progress = computed(() => path.value?.path_data.length ? Math.round(completedCount.value / path.value.path_data.length * 100) : 0)
  const remainingMinutes = computed(() => path.value?.path_data.filter((step) => step.status !== 'completed').reduce((sum, step) => sum + step.estimated_minutes, 0) ?? 0)

  async function load() {
    loading.value = true; error.value = ''
    try { path.value = (await http.get<LearningPath>('/api/path/current')).data }
    catch (cause) { if (cause instanceof ApiError && cause.status === 404) path.value = null; else error.value = cause instanceof Error ? cause.message : '路径加载失败' }
    finally { loading.value = false }
  }
  async function generate(input: GeneratePathInput) {
    generating.value = true; error.value = ''
    try { path.value = (await http.post<LearningPath>('/api/path/generate', input, { timeout: 60000 })).data }
    catch (cause) { error.value = cause instanceof Error ? cause.message : '路径生成失败'; throw cause }
    finally { generating.value = false }
  }
  async function updateStep(step: number, status: PathStepStatus) {
    if (!path.value) return
    updatingStep.value = step; error.value = ''
    try { path.value = (await http.patch<LearningPath>(`/api/path/${path.value.id}/progress`, { step, status })).data }
    catch (cause) { error.value = cause instanceof Error ? cause.message : '进度更新失败'; throw cause }
    finally { updatingStep.value = null }
  }
  return { path, loading, generating, updatingStep, error, completedCount, progress, remainingMinutes, load, generate, updateStep }
})
