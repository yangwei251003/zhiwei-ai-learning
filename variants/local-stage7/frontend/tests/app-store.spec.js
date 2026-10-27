import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

import { useAppStore } from '@/stores/app'

describe('app theme store', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('uses the persisted theme and applies it to the document', () => {
    localStorage.setItem('xzxx-theme', 'dark')
    const store = useAppStore()

    store.initializeTheme()

    expect(store.theme).toBe('dark')
    expect(document.documentElement.dataset.theme).toBe('dark')
  })

  it('toggles and persists the active theme', () => {
    const store = useAppStore()
    store.setTheme('light')
    store.toggleTheme()

    expect(store.theme).toBe('dark')
    expect(localStorage.getItem('xzxx-theme')).toBe('dark')
  })
})
