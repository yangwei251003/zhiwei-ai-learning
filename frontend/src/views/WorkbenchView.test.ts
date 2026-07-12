// @vitest-environment jsdom
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import WorkbenchView from './WorkbenchView.vue'
import { useUserStore } from '../stores/user'

const replace = vi.fn()
vi.mock('vue-router', () => ({ useRouter: () => ({ replace }) }))

describe('WorkbenchView', () => {
  beforeEach(() => {
    replace.mockReset()
    setActivePinia(createPinia())
  })

  it('shows the learning workspace and signed-in username', () => {
    useUserStore().user = { id: 1, username: 'student', email: 'student@example.com', learning_style: 'visual' }
    const wrapper = mount(WorkbenchView, { global: { stubs: { ElButton: { template: '<button><slot /></button>' }, ElIcon: true } } })

    expect(wrapper.text()).toContain('学习流程')
    expect(wrapper.text()).toContain('后端服务')
    expect(wrapper.text()).toContain('Agent 协作')
    expect(wrapper.text()).toContain('每日挑战')
    expect(wrapper.text()).toContain('student')
  })

  it('logs out and replaces the route with login', async () => {
    const store = useUserStore()
    store.token = 'token'
    store.user = { id: 1, username: 'student', email: 'student@example.com', learning_style: 'visual' }
    const logout = vi.spyOn(store, 'logout')
    const wrapper = mount(WorkbenchView, { global: { stubs: { ElButton: { template: '<button v-bind="$attrs"><slot /></button>' }, ElIcon: true } } })

    await wrapper.get('[aria-label="退出登录"]').trigger('click')

    expect(logout).toHaveBeenCalledOnce()
    expect(replace).toHaveBeenCalledWith('/login')
  })
})
