import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import * as authApi from '@/api/auth'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('xzxx-token') || '')
  const user = ref(null)
  const loading = ref(false)
  const error = ref('')
  const isAuthenticated = computed(() => Boolean(token.value))

  function saveToken(value) {
    token.value = value
    localStorage.setItem('xzxx-token', value)
  }

  async function login(payload) {
    loading.value = true
    error.value = ''
    try {
      const result = await authApi.login(payload)
      saveToken(result.access_token)
      user.value = await authApi.getMe()
      return user.value
    } catch (reason) {
      error.value = reason.message
      throw reason
    } finally {
      loading.value = false
    }
  }

  async function register(payload) {
    loading.value = true
    error.value = ''
    try {
      await authApi.register(payload)
      return await login({ email: payload.email, password: payload.password })
    } catch (reason) {
      error.value = reason.message
      throw reason
    } finally {
      loading.value = false
    }
  }

  async function loadMe() {
    if (!token.value) return null
    try {
      user.value = await authApi.getMe()
      return user.value
    } catch (reason) {
      logout()
      throw reason
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('xzxx-token')
  }

  return { token, user, loading, error, isAuthenticated, login, register, loadMe, logout }
})
