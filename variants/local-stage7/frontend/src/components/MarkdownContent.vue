<script setup>
import { computed } from 'vue'
import { renderMarkdown } from '@/utils/markdown'

const props = defineProps({ source: { type: String, default: '' } })
const content = computed(() => renderMarkdown(props.source))
</script>

<template><div class="markdown-content" v-html="content" /></template>
