// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import RegisterView from './RegisterView.vue'

const register = vi.fn()
const saveProfile = vi.fn()
vi.mock('../stores/user', () => ({ useUserStore: () => ({ register, saveProfile }) }))

async function mounted() {
  const router = createRouter({ history: createMemoryHistory(), routes: [
    { path: '/register', component: RegisterView },
    { path: '/login', component: { template: '<div>login</div>' } },
    { path: '/workbench', component: { template: '<div>workbench</div>' } },
  ] })
  await router.push('/register'); await router.isReady()
  return { router, wrapper: mount(RegisterView, { global: { plugins: [router] } }) }
}

const payload = { username: 'learner', password: 'password8', major: '人工智能', learningStyle: 'hands_on' }

describe('RegisterView', () => {
  beforeEach(() => { register.mockReset(); saveProfile.mockReset(); vi.useFakeTimers() })

  it('shows the exact welcome message and redirects after a complete registration', async () => {
    register.mockResolvedValue({ profileSaved: true })
    const { router, wrapper } = await mounted()
    wrapper.getComponent({ name: 'RegisterForm' }).vm.$emit('submit', payload)
    await flushPromises()
    expect(register).toHaveBeenCalledWith({ username: 'learner', password: 'password8', major: '人工智能', cognitive_style: 'hands_on' })
    expect(wrapper.text()).toContain('欢迎加入！我是小智析析，准备好一起学习了吗？')
    expect(wrapper.getComponent({ name: 'AuthShell' }).props('celebrating')).toBe(true)
    await vi.advanceTimersByTimeAsync(420)
    expect(router.currentRoute.value.path).toBe('/workbench')
  })

  it('keeps partial registration on screen and offers a profile retry', async () => {
    register.mockResolvedValue({ profileSaved: false })
    const { router, wrapper } = await mounted()
    wrapper.getComponent({ name: 'RegisterForm' }).vm.$emit('submit', payload)
    await flushPromises()
    expect(wrapper.text()).toContain('账户已创建，画像资料暂未保存')
    expect(wrapper.get('button[data-test="retry-profile"]').text()).toContain('重试保存画像')
    expect(router.currentRoute.value.path).toBe('/register')
  })

  it('does not invent a learning style when the optional choice is omitted', async () => {
    register.mockResolvedValue({ profileSaved: false })
    const { wrapper } = await mounted()
    wrapper.getComponent({ name: 'RegisterForm' }).vm.$emit('submit', { username: 'learner', password: 'password8', major: '网络工程' })
    await flushPromises()
    expect(register).toHaveBeenCalledWith({ username: 'learner', password: 'password8', major: '网络工程', cognitive_style: undefined })
  })

  it('retries only profile saving and redirects after success', async () => {
    register.mockResolvedValue({ profileSaved: false }); saveProfile.mockResolvedValue(undefined)
    const { router, wrapper } = await mounted()
    wrapper.getComponent({ name: 'RegisterForm' }).vm.$emit('submit', payload)
    await flushPromises()
    await wrapper.get('[data-test="retry-profile"]').trigger('click')
    await flushPromises()
    expect(register).toHaveBeenCalledTimes(1)
    expect(saveProfile).toHaveBeenCalledWith('人工智能', 'hands_on')
    expect(wrapper.text()).toContain('欢迎加入！我是小智析析，准备好一起学习了吗？')
    await vi.advanceTimersByTimeAsync(420)
    expect(router.currentRoute.value.path).toBe('/workbench')
  })

  it('shows retry failures and permits another retry', async () => {
    register.mockResolvedValue({ profileSaved: false }); saveProfile.mockRejectedValueOnce(new Error('画像服务繁忙')).mockResolvedValue(undefined)
    const { wrapper } = await mounted()
    wrapper.getComponent({ name: 'RegisterForm' }).vm.$emit('submit', payload)
    await flushPromises()
    await wrapper.get('[data-test="retry-profile"]').trigger('click'); await flushPromises()
    expect(wrapper.text()).toContain('画像服务繁忙')
    expect(wrapper.find('[data-test="retry-profile"]').exists()).toBe(true)
    await wrapper.get('[data-test="retry-profile"]').trigger('click'); await flushPromises()
    expect(saveProfile).toHaveBeenCalledTimes(2)
  })

  it('clears a registration error when the form is edited', async () => {
    register.mockRejectedValue(new Error('注册服务繁忙'))
    const { wrapper } = await mounted()
    wrapper.getComponent({ name: 'RegisterForm' }).vm.$emit('submit', payload); await flushPromises()
    expect(wrapper.text()).toContain('注册服务繁忙')
    wrapper.getComponent({ name: 'RegisterForm' }).vm.$emit('clear-error'); await wrapper.vm.$nextTick()
    expect(wrapper.text()).not.toContain('注册服务繁忙')
  })

  it('does not navigate when unmounted during celebration', async () => {
    register.mockResolvedValue({ profileSaved: true })
    const { router, wrapper } = await mounted()
    const replace = vi.spyOn(router, 'replace')
    wrapper.getComponent({ name: 'RegisterForm' }).vm.$emit('submit', payload); await flushPromises()
    wrapper.unmount(); await vi.advanceTimersByTimeAsync(420)
    expect(replace).not.toHaveBeenCalled()
  })

  it('ignores a pending registration result after unmount', async () => {
    let resolve!: (value: { profileSaved: boolean }) => void
    register.mockReturnValue(new Promise((done) => { resolve = done }))
    const { router, wrapper } = await mounted()
    const replace = vi.spyOn(router, 'replace')
    wrapper.getComponent({ name: 'RegisterForm' }).vm.$emit('submit', payload)
    wrapper.unmount(); resolve({ profileSaved: true }); await flushPromises(); await vi.advanceTimersByTimeAsync(420)
    expect(replace).not.toHaveBeenCalled()
  })
})
