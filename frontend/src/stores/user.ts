import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import type { Credentials, LearningStyle, RegistrationInput, User } from '../types/auth'
import http, { setAuthTokenProvider, setUnauthorizedHandler } from '../utils/http'

const TOKEN_KEY = 'zhiwei.auth.token'

export interface UserRegistrationInput extends RegistrationInput {
  major: string
  cognitive_style: string
}

export const useUserStore = defineStore('user', () => {
  const token = ref<string | null>(null)
  const user = ref<User | null>(null)
  const sessionRestored = ref(false)
  let restoration: Promise<void> | null = null
  const isAuthenticated = computed(() => Boolean(token.value && user.value))

  function persistToken(value: string | null) {
    token.value = value
    if (value) localStorage.setItem(TOKEN_KEY, value)
    else localStorage.removeItem(TOKEN_KEY)
  }

  function logout() {
    persistToken(null)
    user.value = null
  }

  async function loadCurrentUser() {
    const response = await http.get<User>('/api/auth/me')
    user.value = response.data
  }

  async function login(credentials: Credentials) {
    const response = await http.post<{ access_token: string }>('/api/auth/login', credentials)
    persistToken(response.data.access_token)
    await loadCurrentUser()
  }

  function restoreSession(): Promise<void> {
    if (sessionRestored.value) return Promise.resolve()
    if (!restoration) {
      restoration = (async () => {
        const persistedToken = localStorage.getItem(TOKEN_KEY)
        if (persistedToken) {
          persistToken(persistedToken)
          try {
            await loadCurrentUser()
          } catch {
            logout()
          }
        }
        sessionRestored.value = true
      })()
    }
    return restoration
  }

  async function saveProfile(major: string, learningStyle?: LearningStyle | string) {
    await http.patch('/api/profile/current', {
      major,
      ...(learningStyle === undefined ? {} : { cognitive_style: learningStyle }),
    })
  }

  async function register(input: UserRegistrationInput): Promise<{ profileSaved: boolean }> {
    const { major, cognitive_style, ...credentials } = input
    const response = await http.post<{ access_token: string }>('/api/auth/register', credentials)
    persistToken(response.data.access_token)
    await loadCurrentUser()
    try {
      await saveProfile(major, cognitive_style)
      return { profileSaved: true }
    } catch {
      return { profileSaved: false }
    }
  }

  setAuthTokenProvider(() => token.value)
  setUnauthorizedHandler(logout)

  return { isAuthenticated, login, logout, register, restoreSession, saveProfile, sessionRestored, token, user }
})
