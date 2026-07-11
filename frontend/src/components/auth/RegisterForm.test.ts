// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import RegisterForm from './RegisterForm.vue'

async function fillRequired(wrapper: ReturnType<typeof mount>) {
  await wrapper.get('input[autocomplete="username"]').setValue('learner')
  await wrapper.get('input[autocomplete="new-password"]').setValue('password8')
  await wrapper.get('[role="combobox"]').setValue('软件工程')
}

describe('RegisterForm', () => {
  it('filters majors from live input and permits free text', async () => {
    const wrapper = mount(RegisterForm, { attachTo: document.body })
    const major = wrapper.get('[role="combobox"]')
    await major.setValue('数据')
    expect(wrapper.findAll('[role="option"]').map((item) => item.text())).toEqual(['数据科学与大数据技术'])
    await major.setValue('量子信息工程')
    expect(wrapper.findAll('[role="option"]')).toHaveLength(0)
    await fillRequired(wrapper)
    await major.setValue('量子信息工程')
    await wrapper.get('form').trigger('submit')
    expect(wrapper.emitted('submit')?.[0]?.[0]).toMatchObject({ major: '量子信息工程' })
    wrapper.unmount()
  })

  it('blocks passwords shorter than eight characters', async () => {
    const wrapper = mount(RegisterForm)
    await wrapper.get('input[autocomplete="username"]').setValue('learner')
    await wrapper.get('input[autocomplete="new-password"]').setValue('short')
    await wrapper.get('[role="combobox"]').setValue('人工智能')
    await wrapper.get('form').trigger('submit')
    expect(wrapper.text()).toContain('密码至少需要 8 个字符')
    expect(wrapper.emitted('submit')).toBeUndefined()
  })

  it('maps 动手型 to hands_on and allows no learning style', async () => {
    const wrapper = mount(RegisterForm)
    await fillRequired(wrapper)
    await wrapper.get('input[value="hands_on"]').setValue(true)
    await wrapper.get('form').trigger('submit')
    expect(wrapper.emitted('submit')?.[0]?.[0]).toEqual({ username: 'learner', password: 'password8', major: '软件工程', learningStyle: 'hands_on' })

    const optional = mount(RegisterForm)
    await fillRequired(optional)
    await optional.get('form').trigger('submit')
    expect(optional.emitted('submit')?.[0]?.[0]).toEqual({ username: 'learner', password: 'password8', major: '软件工程' })
  })

  it('supports keyboard selection with complete combobox ARIA', async () => {
    const wrapper = mount(RegisterForm)
    const combo = wrapper.get('[role="combobox"]')
    expect(combo.attributes('aria-controls')).toBe('register-major-listbox')
    expect(combo.attributes('aria-expanded')).toBe('false')
    await combo.trigger('focus')
    await combo.setValue('工程')
    await combo.trigger('keydown', { key: 'ArrowDown' })
    expect(combo.attributes('aria-expanded')).toBe('true')
    expect(combo.attributes('aria-activedescendant')).toBeTruthy()
    await combo.trigger('keydown', { key: 'Enter' })
    expect(combo.element).toHaveProperty('value', '软件工程')
    expect(combo.attributes('aria-expanded')).toBe('false')
    await combo.trigger('keydown', { key: 'Escape' })
  })

  it('disables every control while loading', () => {
    const wrapper = mount(RegisterForm, { props: { loading: true } })
    expect(wrapper.findAll('input').every((input) => input.attributes('disabled') !== undefined)).toBe(true)
    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('[data-test="password-toggle"]').attributes('disabled')).toBeDefined()
  })
})
