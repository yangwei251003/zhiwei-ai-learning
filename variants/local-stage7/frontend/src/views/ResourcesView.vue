<script setup>
import { PhMagnifyingGlass as MagnifyingGlass, PhSlidersHorizontal as SlidersHorizontal, PhX as X } from '@phosphor-icons/vue'
import { computed, onMounted, ref } from 'vue'

import MarkdownContent from '@/components/MarkdownContent.vue'
import MermaidDiagram from '@/components/MermaidDiagram.vue'
import PageHeader from '@/components/PageHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import { getResource, listResources } from '@/api/resources'
import { formatDate, resourceLabels } from '@/utils/format'
import { handleTabKeydown } from '@/utils/tabs'

const types = [
  { value: '', label: '全部资源' }, { value: 'document', label: '讲解文档' },
  { value: 'mindmap', label: '思维导图' }, { value: 'quiz', label: '练习题' },
  { value: 'video', label: '视频脚本' }, { value: 'code', label: '代码案例' },
]
const resources = ref([])
const loading = ref(true)
const error = ref('')
const type = ref('')
const search = ref('')
const sort = ref('latest')
const selected = ref(null)
const drawerOpen = computed({
  get: () => Boolean(selected.value),
  set: (value) => { if (!value) selected.value = null },
})
const detailLoading = ref(false)
const detailError = ref('')
const activeLabel = computed(() => types.find((item) => item.value === type.value)?.label || '全部资源')

function selectType(value) { type.value = value; load() }

async function load() {
  loading.value = true; error.value = ''
  try { resources.value = await listResources({ type: type.value || undefined, search: search.value || undefined, sort: sort.value }) }
  catch (reason) { error.value = reason.message }
  finally { loading.value = false }
}

async function openResource(resource) {
  selected.value = resource; detailLoading.value = true; detailError.value = ''
  try { selected.value = await getResource(resource.id) }
  catch (reason) { detailError.value = reason.message }
  finally { detailLoading.value = false }
}

function normalizedType(resource) { return resource.resource_type || resource.type }
onMounted(load)
</script>

<template>
  <div class="resources-page">
    <PageHeader title="学习资源库" description="讲解、图解、练习、视频脚本与代码都来自真实对话生成，并保留创建时间。">
      <template #actions><RouterLink class="primary-button" to="/chat">生成新资源</RouterLink></template>
    </PageHeader>

    <section class="resource-toolbar" aria-label="资源筛选">
      <form class="resource-search" @submit.prevent="load"><label class="sr-only" for="resource-search">搜索资源</label><MagnifyingGlass :size="19" /><input id="resource-search" v-model.trim="search" placeholder="搜索标题或内容" /><button type="submit">搜索</button></form>
      <div class="type-tabs" role="tablist" aria-label="资源类型"><button v-for="(item, index) in types" :id="`resource-tab-${item.value || 'all'}`" :key="item.value" type="button" role="tab" aria-controls="resource-panel" :aria-selected="type === item.value" :tabindex="type === item.value ? 0 : -1" :class="{ active: type === item.value }" @click="selectType(item.value)" @keydown="handleTabKeydown($event, index, types, selectType)">{{ item.label }}</button></div>
      <label class="sort-control"><SlidersHorizontal :size="18" /><span class="sr-only">排序方式</span><select v-model="sort" @change="load"><option value="latest">最近生成</option><option value="oldest">最早生成</option></select></label>
    </section>

    <div id="resource-panel" role="tabpanel" :aria-labelledby="`resource-tab-${type || 'all'}`">
      <StatePanel v-if="loading" state="loading" />
      <StatePanel v-else-if="error" state="error" title="资源库暂未连接" :message="error" action-label="重新加载" @action="load" />
      <StatePanel v-else-if="!resources.length" state="empty" :title="`${activeLabel}还没有内容`" message="从一次真实学习对话开始，生成的材料会自动沉淀到这里。" action-label="去学习对话" @action="$router.push('/chat')" />
      <section v-else class="resource-grid" aria-live="polite">
        <button v-for="resource in resources" :key="resource.id" class="resource-item" type="button" @click="openResource(resource)">
          <span class="resource-icon"><img :src="`/assets/${normalizedType(resource)}.svg`" width="34" height="34" alt="" /></span>
          <span class="resource-type">{{ resourceLabels[normalizedType(resource)] || normalizedType(resource) }}</span>
          <strong>{{ resource.title }}</strong>
          <span class="resource-excerpt">{{ resource.content.replace(/[#*`|]/g, '').slice(0, 110) }}</span>
          <span class="resource-meta"><span>{{ resource.difficulty || '未标难度' }}</span><time>{{ formatDate(resource.created_at) }}</time></span>
        </button>
      </section>
    </div>

    <ElDrawer v-model="drawerOpen" size="min(760px, 92vw)" :show-close="false" destroy-on-close>
      <template #header><div class="detail-header"><div><span>{{ selected ? resourceLabels[normalizedType(selected)] || normalizedType(selected) : '' }}</span><h2>{{ selected?.title }}</h2></div><button class="icon-button" type="button" aria-label="关闭资源详情" @click="selected = null"><X :size="20" /></button></div></template>
      <StatePanel v-if="detailLoading" state="loading" />
      <div v-else-if="detailError" class="inline-error" role="alert">{{ detailError }}</div>
      <MermaidDiagram v-else-if="selected && normalizedType(selected) === 'mindmap'" :source="selected.content" />
      <MarkdownContent v-else-if="selected" :source="selected.content" />
    </ElDrawer>
  </div>
</template>

<style scoped>
.resource-toolbar { position: sticky; top: 76px; z-index: 10; display: grid; grid-template-columns: minmax(220px, 1fr) auto auto; gap: 14px; align-items: center; margin-bottom: 26px; padding: 12px; border: 1px solid var(--color-border); border-radius: var(--radius-card); background: color-mix(in srgb, var(--color-surface) 92%, transparent); backdrop-filter: blur(12px); }
.resource-search { display: flex; align-items: center; gap: 8px; min-height: 42px; padding-left: 11px; border: 1px solid var(--color-border); border-radius: var(--radius-control); background: var(--color-surface); }.resource-search svg { color: var(--color-ink-secondary); }.resource-search input { min-width: 0; flex: 1; border: 0; background: transparent; color: var(--color-ink); }.resource-search button { align-self: stretch; padding: 0 13px; border: 0; border-left: 1px solid var(--color-border); background: transparent; color: var(--color-brand-action); font-weight: 800; cursor: pointer; }
.type-tabs { display: flex; overflow-x: auto; gap: 4px; }.type-tabs button { min-height: 40px; padding: 7px 10px; border: 0; border-radius: 8px; background: transparent; color: var(--color-ink-secondary); white-space: nowrap; cursor: pointer; }.type-tabs button.active { background: var(--color-brand-soft); color: var(--color-brand-action); font-weight: 800; }
.sort-control { display: flex; align-items: center; gap: 5px; }.sort-control select { min-height: 40px; border: 0; background: transparent; color: var(--color-ink); }
.resource-grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 14px; }.resource-item { display: grid; grid-column: span 4; min-height: 248px; align-content: start; gap: 9px; padding: 22px; border: 1px solid var(--color-border); border-radius: var(--radius-card); background: var(--color-surface); color: var(--color-ink); text-align: left; cursor: pointer; transition: transform var(--duration-base) var(--ease-out), border-color var(--duration-fast) ease; }.resource-item:nth-child(5n + 1), .resource-item:nth-child(5n + 4) { grid-column: span 6; }.resource-item:hover { transform: translateY(-4px); border-color: color-mix(in srgb, var(--color-brand) 45%, var(--color-border)); }.resource-item:active { transform: translateY(-1px) scale(.99); }
.resource-icon { display: grid; width: 50px; height: 50px; margin-bottom: 4px; place-items: center; border-radius: var(--radius-control); background: var(--color-brand-soft); }.resource-type { color: var(--color-brand-action); font-size: 12px; font-weight: 800; }.resource-item strong { font-size: 18px; line-height: 1.35; }.resource-excerpt { overflow: hidden; color: var(--color-ink-secondary); font-size: 14px; line-height: 1.55; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; }.resource-meta { display: flex; justify-content: space-between; gap: 12px; margin-top: auto; padding-top: 12px; border-top: 1px solid var(--color-border); color: var(--color-ink-secondary); font-size: 12px; }
.detail-header { display: flex; width: 100%; justify-content: space-between; gap: 20px; }.detail-header span { color: var(--color-brand-action); font-size: 13px; font-weight: 800; }.detail-header h2 { margin: 4px 0 0; font-size: 24px; }
@media (max-width: 1120px) { .resource-toolbar { grid-template-columns: 1fr auto; }.type-tabs { grid-column: 1 / -1; grid-row: 2; }.resource-item, .resource-item:nth-child(5n + 1), .resource-item:nth-child(5n + 4) { grid-column: span 6; } }
@media (max-width: 680px) { .resource-toolbar { position: static; grid-template-columns: 1fr; }.type-tabs, .sort-control { grid-column: auto; grid-row: auto; }.resource-grid { grid-template-columns: 1fr; }.resource-item, .resource-item:nth-child(5n + 1), .resource-item:nth-child(5n + 4) { grid-column: auto; }.resource-item { min-height: 220px; } }
@media (prefers-reduced-motion: reduce) { .resource-item { transition: border-color 1ms linear; }.resource-item:hover { transform: none; } }
</style>
