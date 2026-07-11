// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import LoginView from './LoginView.vue'

const login = vi.fn()
vi.mock('../stores/user', () => ({ useUserStore: () => ({ login }) }))

async function mountAt(location: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/login', component: LoginView },
      { path: '/workbench', component: { template: '<div>workbench</div>' } },
      { path: '/register', component: { template: '<div>register</div>' } },
      { path: '/lesson/:id', component: { template: '<div>lesson</div>' } },
    ],
  })
  await router.push(location)
  await router.isReady()
  return { router, wrapper: mount(LoginView, { global: { plugins: [router] } }) }
}

describe('LoginView', () => {
  beforeEach(() => { login.mockReset(); vi.useFakeTimers() })

  it('shows normalized failures and restarts the one-shot shake', async () => {
    login.mockRejectedValue(new Error('账号或密码错误'))
    const { wrapper } = await mountAt('/login')
    await wrapper.getComponent({ name: 'LoginForm' }).vm.$emit('submit', { username: 'a', password: 'b', remember: false })
    await vi.waitFor(() => expect(wrapper.text()).toContain('账号或密码错误'))
    const firstKey = wrapper.get('[data-test="login-panel"]').attributes('data-shake-key')
    await wrapper.getComponent({ name: 'LoginForm' }).vm.$emit('submit', { username: 'a', password: 'b', remember: false })
    await vi.waitFor(() => expect(wrapper.get('[data-test="login-panel"]').attributes('data-shake-key')).not.toBe(firstKey))
  })

  it.each([
    ['https://evil.example', '/workbench'],
    ['//evil.example/path', '/workbench'],
    ['/javascript:alert(1)', '/workbench'],
    ['/lesson\\42', '/workbench'],
    ['/lesson/42?tab=notes#today', '/lesson/42?tab=notes#today'],
  ])('celebrates then safely redirects %s', async (redirect, expected) => {
    login.mockResolvedValue(undefined)
    const { router, wrapper } = await mountAt(`/login?redirect=${encodeURIComponent(redirect)}`)
    await wrapper.getComponent({ name: 'LoginForm' }).vm.$emit('submit', { username: 'a', password: 'b', remember: true })
    await vi.waitFor(() => expect(wrapper.find('.success-curtain').exists()).toBe(true))
    expect(wrapper.getComponent({ name: 'AuthShell' }).props('celebrating')).toBe(true)
    expect(wrapper.text()).toContain('登录成功')
    await vi.advanceTimersByTimeAsync(420)
    expect(router.currentRoute.value.fullPath).toBe(expected)
  })
})
