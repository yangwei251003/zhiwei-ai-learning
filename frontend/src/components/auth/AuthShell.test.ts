// @vitest-environment jsdom
import { afterEach, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import AuthShell from './AuthShell.vue'

afterEach(() => {
  document.documentElement.classList.remove('dark')
  localStorage.clear()
})

describe('AuthShell', () => {
  it('renders its brand message, facts, content and footer slots', () => {
    const wrapper = mount(AuthShell, {
      slots: {
        default: '<form data-test="auth-form">Sign in</form>',
        footer: '<a data-test="auth-footer">Help</a>',
      },
    })

    expect(wrapper.text()).toContain('知微智学')
    expect(wrapper.text()).toContain('学习，从被理解开始')
    expect(wrapper.text()).toContain('多智能体')
    expect(wrapper.text()).toContain('个性化')
    expect(wrapper.text()).toContain('即时生成')
    expect(wrapper.get('[data-test="auth-form"]').element.tagName).toBe('FORM')
    expect(wrapper.get('[data-test="auth-footer"]').element.tagName).toBe('A')
  })

  it('toggles and persists the document theme', async () => {
    const wrapper = mount(AuthShell)
    const button = wrapper.get('[data-test="theme-toggle"]')

    await button.trigger('click')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(localStorage.getItem('zhiwei.theme')).toBe('dark')

    await button.trigger('click')
    expect(document.documentElement.classList.contains('dark')).toBe(false)
    expect(localStorage.getItem('zhiwei.theme')).toBe('light')
  })
})
