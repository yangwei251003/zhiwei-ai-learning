// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import LoginForm from './LoginForm.vue'

describe('LoginForm', () => {
  it('shows both required messages when submitted empty', async () => {
    const wrapper = mount(LoginForm)
    await wrapper.get('form').trigger('submit')
    expect(wrapper.text()).toContain('请输入用户名')
    expect(wrapper.text()).toContain('请输入密码')
    expect(wrapper.emitted('submit')).toBeUndefined()
  })

  it('toggles password visibility with an accessible control', async () => {
    const wrapper = mount(LoginForm)
    const password = wrapper.get('input[autocomplete="current-password"]')
    const toggle = wrapper.get('[data-test="password-toggle"]')
    expect(password.attributes('type')).toBe('password')
    await toggle.trigger('click')
    expect(password.attributes('type')).toBe('text')
    expect(toggle.attributes('aria-label')).toBe('隐藏密码')
  })

  it('emits the exact credentials for a valid submission', async () => {
    const wrapper = mount(LoginForm)
    await wrapper.get('input[autocomplete="username"]').setValue('learner')
    await wrapper.get('input[autocomplete="current-password"]').setValue('old')
    await wrapper.get('input[type="checkbox"]').setValue(true)
    await wrapper.get('form').trigger('submit')
    expect(wrapper.emitted('submit')).toEqual([[{ username: 'learner', password: 'old', remember: true }]])
  })

  it('disables all form controls while loading', () => {
    const wrapper = mount(LoginForm, { props: { loading: true } })
    expect(wrapper.findAll('input').every((input) => input.attributes('disabled') !== undefined)).toBe(true)
    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('[data-test="password-toggle"]').attributes('disabled')).toBeDefined()
  })

  it('only describes inputs with error elements that are actually rendered', async () => {
    const wrapper = mount(LoginForm)
    const username = () => wrapper.get('input[autocomplete="username"]')

    expect(username().attributes('aria-describedby')).toBeUndefined()

    await wrapper.get('form').trigger('submit')
    expect(username().attributes('aria-describedby')).toBe('login-username-error')
    expect(wrapper.find('#login-username-error').exists()).toBe(true)
    expect(wrapper.find('#login-server-error').exists()).toBe(false)

    await wrapper.setProps({ serverError: '账号或密码错误' })
    await username().setValue('learner')
    expect(username().attributes('aria-describedby')).toBe('login-server-error')
    expect(wrapper.find('#login-username-error').exists()).toBe(false)
    expect(wrapper.find('#login-server-error').exists()).toBe(true)

    await username().setValue('')
    await wrapper.get('form').trigger('submit')
    expect(username().attributes('aria-describedby')).toBe('login-username-error login-server-error')
  })
})
