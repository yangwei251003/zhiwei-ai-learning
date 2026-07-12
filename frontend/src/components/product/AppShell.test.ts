// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { describe, expect, it } from 'vitest'

import AppShell from './AppShell.vue'

describe('AppShell', () => {
  it('renders every primary product destination and page content', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: ['/', '/workbench', '/chat', '/resources', '/path', '/tutor', '/admin'].map((path) => ({
        path,
        component: { template: '<div />' },
      })),
    })
    await router.push('/')
    const wrapper = mount(AppShell, {
      slots: { default: '<p>页面内容</p>' },
      global: { plugins: [createPinia(), router], stubs: { RouterLink: false } },
    })
    expect(wrapper.text()).toContain('页面内容')
    for (const label of ['首页', '对话', '资源库', '学习路径', '智能辅导', '管理后台']) {
      expect(wrapper.text()).toContain(label)
    }
  })
})
