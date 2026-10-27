<script setup lang="ts">
import type { LearningResource } from '../../types/product'

defineProps<{ resource: LearningResource }>()
defineEmits<{ select: [id: number] }>()
const labels: Record<string, string> = {
  document: '讲解文档', mindmap: '思维导图', quiz: '随堂测验', video_script: '视频脚本', code_case: '代码案例',
}
</script>

<template>
  <article class="resource-card">
    <div class="resource-icon"><img :src="`/assets/icon-${resource.resource_type === 'video_script' ? 'video' : resource.resource_type === 'code_case' ? 'code' : resource.resource_type}.svg`" alt="" loading="lazy" /></div>
    <div><span class="eyebrow">{{ labels[resource.resource_type] || '学习资源' }}</span><h3>{{ resource.title }}</h3><p>{{ resource.content.slice(0, 92) }}</p></div>
    <button class="card-action" @click="$emit('select', resource.id)">查看详情 <span>→</span></button>
  </article>
</template>
