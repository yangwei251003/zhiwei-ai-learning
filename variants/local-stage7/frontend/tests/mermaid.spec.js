import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import MermaidDiagram from '@/components/MermaidDiagram.vue'
import { extractMermaidSource } from '@/utils/mermaid'

const render = vi.fn(async () => ({ svg: '<svg aria-label="diagram"></svg>' }))

vi.mock('mermaid', () => ({
  default: {
    initialize: vi.fn(),
    render,
  },
}))

describe('MermaidDiagram', () => {
  beforeEach(() => render.mockClear())

  it('renders only the first fenced Mermaid block from a mixed real response', async () => {
    const mixedContent = [
      '为了帮助学生学习二叉树遍历，先给出结构图。',
      '```mermaid',
      'graph TD;',
      'A[二叉树] --> B[前序遍历]',
      '```',
      '随后是可运行代码：',
      '```python',
      'print("tree")',
      '```',
    ].join('\n')

    mount(MermaidDiagram, { props: { source: mixedContent } })
    await vi.waitFor(() => expect(render).toHaveBeenCalledOnce())

    expect(render.mock.calls[0][1]).toBe('graph TD;\nA[二叉树] --> B[前序遍历]')
  })
})

describe('extractMermaidSource', () => {
  it('returns an empty source instead of sending prose to Mermaid', () => {
    expect(extractMermaidSource('这里暂时只有讲解正文，没有图解源码。')).toBe('')
  })
})
