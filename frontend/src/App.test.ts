// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import App from './App.vue'

describe('App', () => {
  it('defines the route fade and visually hides live announcements', () => {
    const styles = readFileSync('src/styles/main.scss', 'utf8')
    expect(styles).toContain('.auth-route-enter-active')
    expect(styles).toContain('.sr-only')
  })

  it('renders routed content and announces the current page', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/login', component: { template: '<p>Login content</p>' }, meta: { title: '登录' } },
        { path: '/workbench', component: { template: '<p>Workbench content</p>' }, meta: { title: '学习工作台' } },
      ],
    })
    await router.push('/login')
    await router.isReady()
    const wrapper = mount(App, { global: { plugins: [router] } })

    expect(wrapper.text()).toContain('Login content')
    expect(wrapper.get('[aria-live="polite"]').text()).toBe('已进入登录')
    await router.push('/workbench')
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('Workbench content')
    expect(wrapper.get('[aria-live="polite"]').text()).toBe('已进入学习工作台')
  })
})
