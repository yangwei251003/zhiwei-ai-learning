// @vitest-environment jsdom
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import WorkbenchView from './WorkbenchView.vue'
import { useUserStore } from '../stores/user'

const replace = vi.fn()
const push = vi.fn()
vi.mock('vue-router', () => ({
  RouterLink: { template: '<a><slot /></a>' },
  useRoute: () => ({ path: '/workbench', meta: { title: '首页' } }),
  useRouter: () => ({ push, replace }),
}))
vi.mock('../utils/http', () => ({
  default: { get: vi.fn().mockRejectedValue(new Error('offline')) },
}))

describe('WorkbenchView', () => {
  beforeEach(() => {
    replace.mockReset()
    setActivePinia(createPinia())
  })

  it('shows the product home and signed-in username', () => {
    useUserStore().user = { id: 1, username: 'student', email: 'student@example.com', learning_style: 'visual' }
    const wrapper = mount(WorkbenchView, { global: { stubs: { ElButton: { template: '<button><slot /></button>' }, ElIcon: true } } })

    expect(wrapper.text()).toContain('把好奇心，玩成')
    expect(wrapper.text()).toContain('开始今天的探索')
    expect(wrapper.text()).toContain('从一句问题，到一条自己的路')
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
