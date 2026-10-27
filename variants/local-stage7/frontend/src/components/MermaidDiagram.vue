<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'

import { extractMermaidSource } from '@/utils/mermaid'

const props = defineProps({ source: { type: String, required: true } })
const svg = ref('')
const error = ref('')
let renderVersion = 0

watch(() => props.source, render, { immediate: true })

async function render(source) {
  const version = ++renderVersion
  error.value = ''
  try {
    const { default: mermaid } = await import('mermaid')
    mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', theme: 'base' })
    const result = await mermaid.render(
      `xzxx-diagram-${version}-${Date.now()}`,
      extractMermaidSource(source),
    )
    if (version === renderVersion) svg.value = result.svg
  } catch (reason) {
    if (version === renderVersion) {
      svg.value = ''
      error.value = `图解暂时无法渲染：${reason.message}`
    }
  }
}

onBeforeUnmount(() => { renderVersion += 1 })
</script>

<template>
  <div v-if="svg" class="mermaid-diagram" v-html="svg" />
  <div v-else-if="error" class="inline-error" role="alert">{{ error }}</div>
  <div v-else class="skeleton-line" aria-label="正在渲染图解" />
</template>
