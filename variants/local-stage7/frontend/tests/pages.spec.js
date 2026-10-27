import { fireEvent, render, screen } from '@testing-library/vue'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { describe, expect, it, vi } from 'vitest'

import { apiClient } from '@/api/request'
import { useChatStore } from '@/stores/chat'
import AdminView from '@/views/AdminView.vue'
import ChatView from '@/views/ChatView.vue'
import HomeView from '@/views/HomeView.vue'
import LoginView from '@/views/LoginView.vue'
import PathView from '@/views/PathView.vue'
import RegisterView from '@/views/RegisterView.vue'
import ResourcesView from '@/views/ResourcesView.vue'
import TutorView from '@/views/TutorView.vue'

async function renderPage(component) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/login', component: { template: '<div />' } },
    ],
  })
  await router.push('/')
  await router.isReady()
  return render(component, { global: { plugins: [createPinia(), router] } })
}

describe('the eight Vue pages', () => {
  it.each([
    [LoginView, '继续你的学习旅程'],
    [RegisterView, '建立你的学习画像'],
    [HomeView, '今天从哪里继续'],
    [ChatView, '学习对话'],
    [ResourcesView, '学习资源库'],
    [PathView, '个性化学习路径'],
    [TutorView, '智能辅导'],
    [AdminView, '管理后台'],
  ])('renders the page heading for %p', async (component, heading) => {
    await renderPage(component)
    expect(screen.getByRole('heading', { name: heading, level: 1 })).toBeTruthy()
  })

  it('exposes the three core chat regions', async () => {
    await renderPage(ChatView)

    expect(screen.getByRole('region', { name: '对话历史' })).toBeTruthy()
    expect(screen.getByRole('region', { name: '当前对话' })).toBeTruthy()
    expect(screen.getByRole('region', { name: '六维画像' })).toBeTruthy()
  })

  it('loads and exposes real conversation summaries in the history region', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    vi.spyOn(apiClient, 'get').mockResolvedValueOnce([
      { id: 7, title: '递归复习', message_count: 2, last_message: '递归是函数调用自身' },
    ])
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/', component: { template: '<div />' } }],
    })
    await router.push('/')
    await router.isReady()

    render(ChatView, { global: { plugins: [pinia, router] } })

    expect(await screen.findByRole('button', { name: /递归复习/ })).toBeTruthy()
    expect(useChatStore().history[0].message_count).toBe(2)
  })

  it('moves Tutor tab focus and selection with ArrowRight', async () => {
    await renderPage(TutorView)
    const textTab = screen.getByRole('tab', { name: '文字讲解' })
    const diagramTab = screen.getByRole('tab', { name: '结构图解' })

    textTab.focus()
    await fireEvent.keyDown(textTab, { key: 'ArrowRight' })

    expect(diagramTab.getAttribute('aria-selected')).toBe('true')
    expect(document.activeElement).toBe(diagramTab)
  })

})
