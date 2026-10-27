<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import MarkdownIt from 'markdown-it'
import AppShell from '../components/product/AppShell.vue'
import EmptyState from '../components/product/EmptyState.vue'
import ResourceCard from '../components/product/ResourceCard.vue'
import type { LearningResource } from '../types/product'
import http from '../utils/http'

const route = useRoute(); const router = useRouter(); const resources = ref<LearningResource[]>([]); const selected = ref<LearningResource | null>(null)
const loading = ref(true); const query = ref(''); const filter = ref('all'); const loadMs = ref(0); const error = ref('')
const markdown = new MarkdownIt({ html: false, linkify: true, breaks: true })
const filtered = computed(() => resources.value.filter((item) => (filter.value === 'all' || item.resource_type === filter.value) && item.title.toLowerCase().includes(query.value.toLowerCase())))
const rendered = computed(() => selected.value ? markdown.render(selected.value.content) : '')
async function load() { const start = performance.now(); loading.value = true; try { const response = await http.get('/api/resources/?limit=100'); resources.value = response.data.resources; loadMs.value = Math.round(performance.now() - start); const id = Number(route.query.id); if (id) selected.value = resources.value.find((item) => item.id === id) || (await http.get(`/api/resources/${id}`)).data } catch (cause) { error.value = cause instanceof Error ? cause.message : '资源加载失败' } finally { loading.value = false } }
function open(id: number) { selected.value = resources.value.find((item) => item.id === id) || null; router.replace({ query: { id } }) }
function close() { selected.value = null; router.replace({ query: {} }) }
onMounted(load)
</script>
<template><AppShell><section class="page-header atmosphere-soft"><div><span class="eyebrow">AI 生成资源库</span><h1>每份资料，都是为你而写</h1><p>文档、导图、测验和代码案例会在这里持续沉淀。</p></div><div class="load-metric" v-if="loadMs">列表加载 {{ loadMs }} ms</div></section><section class="resource-toolbar"><input v-model="query" type="search" placeholder="搜索资源标题…" /><div class="filter-tabs"><button v-for="item in [['all','全部'],['document','文档'],['mindmap','导图'],['quiz','测验'],['code_case','代码']]" :key="item[0]" :class="{ active: filter === item[0] }" @click="filter = item[0]">{{ item[1] }}</button></div></section><div v-if="loading" class="card-grid"><div v-for="n in 6" :key="n" class="skeleton-card" /></div><div v-else-if="error" class="error-banner">{{ error }} <button @click="load">重试</button></div><EmptyState v-else-if="!filtered.length" title="资源星球还是空的" description="去对话页告诉小智析析你想学什么，第一份专属资源马上诞生。" action="开始生成" @action="router.push('/chat')" /><div v-else class="card-grid"><ResourceCard v-for="resource in filtered" :key="resource.id" :resource="resource" @select="open" /></div><div v-if="selected" class="modal-backdrop" @click.self="close"><article class="resource-modal"><button class="modal-close" aria-label="关闭" @click="close">×</button><span class="eyebrow">资源详情</span><h1>{{ selected.title }}</h1><div class="markdown-body" v-html="rendered" /></article></div></AppShell></template>
