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
})
