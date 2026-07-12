// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import ResourceCard from './ResourceCard.vue'

describe('ResourceCard', () => {
  it('exposes generated resource metadata and selection', async () => {
    const wrapper = mount(ResourceCard, {
      props: { resource: { id: 7, resource_type: 'document', title: 'Python 变量', content: '# 文档' } },
    })
    expect(wrapper.text()).toContain('Python 变量')
    expect(wrapper.text()).toContain('讲解文档')
    await wrapper.get('button').trigger('click')
    expect(wrapper.emitted('select')?.[0]).toEqual([7])
  })
})
