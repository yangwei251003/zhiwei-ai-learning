// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import BrandConstellation from './BrandConstellation.vue'

describe('BrandConstellation', () => {
  it('renders the semantic nodes and hides decorative layers', () => {
    const wrapper = mount(BrandConstellation, { props: { focused: false } })

    expect(wrapper.findAll('.constellation-node').map((node) => node.text())).toEqual([
      '画像',
      '资源',
      '路径',
    ])
    expect(wrapper.get('.constellation-decoration').attributes('aria-hidden')).toBe('true')
    expect(wrapper.get('img').attributes('alt')).toContain('小智析析')
  })

  it('enhances focus without replacing the structure', async () => {
    const wrapper = mount(BrandConstellation, { props: { focused: false } })
    expect(wrapper.classes()).not.toContain('is-focused')

    await wrapper.setProps({ focused: true })
    expect(wrapper.classes()).toContain('is-focused')
    expect(wrapper.findAll('.constellation-node')).toHaveLength(3)
  })

  it('uses the celebrating mascot when requested', () => {
    const wrapper = mount(BrandConstellation, {
      props: { focused: false, celebrating: true },
    })

    expect(wrapper.get('img').attributes('src')).toBe('/assets/mascot-celebrate.png')
  })
})
