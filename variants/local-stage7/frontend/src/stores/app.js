import { defineStore } from 'pinia'
import { ref } from 'vue'

const STORAGE_KEY = 'xzxx-theme'

function systemTheme() {
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

export const useAppStore = defineStore('app', () => {
  const theme = ref('light')
  const sidebarOpen = ref(false)

  function setTheme(value) {
    theme.value = value === 'dark' ? 'dark' : 'light'
    document.documentElement.dataset.theme = theme.value
    localStorage.setItem(STORAGE_KEY, theme.value)
  }

  function initializeTheme() {
    setTheme(localStorage.getItem(STORAGE_KEY) || systemTheme())
  }

  function toggleTheme() {
    setTheme(theme.value === 'dark' ? 'light' : 'dark')
  }

  return { theme, sidebarOpen, initializeTheme, setTheme, toggleTheme }
})
