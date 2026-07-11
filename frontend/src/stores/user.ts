import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import type { Credentials, LearningStyle, RegistrationInput, User } from '../types/auth'
import http, { ApiError, setAuthTokenProvider, setUnauthorizedHandler } from '../utils/http'

const TOKEN_KEY = 'zhiwei.auth.token'

function readStoredToken(): string | null {
  try {
    return typeof localStorage === 'undefined' ? null : localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

function writeStoredToken(value: string): void {
  try {
    if (typeof localStorage !== 'undefined') localStorage.setItem(TOKEN_KEY, value)
  } catch {
    // Authentication still works in memory when browser storage is unavailable.
  }
}

function removeStoredToken(): void {
  try {
    if (typeof localStorage !== 'undefined') localStorage.removeItem(TOKEN_KEY)
  } catch {
    // Authentication still works in memory when browser storage is unavailable.
  }
}

export interface UserRegistrationInput extends RegistrationInput {
  major: string
  cognitive_style: string
}

export const useUserStore = defineStore('user', () => {
  const token = ref<string | null>(null)
  const user = ref<User | null>(null)
  const sessionRestored = ref(false)
  let restoration: Promise<void> | null = null
  let generation = 0
  const isAuthenticated = computed(() => Boolean(token.value && user.value))

  function persistToken(value: string | null) {
    generation += 1
    token.value = value
    if (value) writeStoredToken(value)
    else removeStoredToken()
  }

  function logout() {
    persistToken(null)
    user.value = null
  }

  async function loadCurrentUser(expectedGeneration: number, expectedToken: string) {
    const response = await http.get<User>('/api/auth/me')
    if (generation === expectedGeneration && token.value === expectedToken) user.value = response.data
  }

  async function login(credentials: Credentials) {
    const response = await http.post<{ access_token: string }>('/api/auth/login', credentials)
    persistToken(response.data.access_token)
    const loginGeneration = generation
    try {
      await loadCurrentUser(loginGeneration, response.data.access_token)
    } catch (cause) {
      if (generation === loginGeneration) logout()
      throw cause
    }
  }

  function restoreSession(): Promise<void> {
    if (sessionRestored.value) return Promise.resolve()
    if (!restoration) {
      restoration = (async () => {
        const persistedToken = readStoredToken()
        if (persistedToken) {
          persistToken(persistedToken)
          const restoreGeneration = generation
          try {
            await loadCurrentUser(restoreGeneration, persistedToken)
          } catch (cause) {
            if (cause instanceof ApiError && cause.status === 401 && generation === restoreGeneration) logout()
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
    const registerGeneration = generation
    try {
      await loadCurrentUser(registerGeneration, response.data.access_token)
    } catch {
      return { profileSaved: false }
    }
    try {
      await saveProfile(major, cognitive_style)
      return { profileSaved: true }
    } catch {
      return { profileSaved: false }
    }
  }

  return { isAuthenticated, login, logout, register, restoreSession, saveProfile, sessionRestored, token, user }
})

export function bindUserStoreToHttp(store: ReturnType<typeof useUserStore>): void {
  setAuthTokenProvider(() => store.token)
  setUnauthorizedHandler(() => store.logout())
}
