<script setup>
import { PhChatsCircle as ChatsCircle, PhPaperPlaneRight as PaperPlaneRight, PhTreeStructure as Diagram, PhVideoCamera as VideoCamera } from '@phosphor-icons/vue'
import { computed, ref } from 'vue'

import MarkdownContent from '@/components/MarkdownContent.vue'
import MermaidDiagram from '@/components/MermaidDiagram.vue'
import PageHeader from '@/components/PageHeader.vue'
import { useChatStore } from '@/stores/chat'
import { handleTabKeydown } from '@/utils/tabs'

const chatStore = useChatStore()
const question = ref('')
const activeTab = ref('text')
const lastAnswer = computed(() => [...chatStore.messages].reverse().find((item) => item.role === 'assistant'))
const diagramSource = computed(() => lastAnswer.value?.content.match(/```mermaid\s*([\s\S]*?)```/)?.[1]?.trim() || '')
const videoScript = computed(() => {
  const content = lastAnswer.value?.content || ''
  const match = content.match(/(?:视频脚本|分镜)[\s\S]*/)
  return match?.[0] || ''
})
const tabs = [
  { value: 'text', label: '文字讲解', icon: ChatsCircle },
  { value: 'diagram', label: '结构图解', icon: Diagram },
  { value: 'video', label: '视频脚本', icon: VideoCamera },
]

function selectTab(value) { activeTab.value = value }

async function ask() {
  const content = question.value.trim()
  if (!content || chatStore.streaming) return
  await chatStore.sendMessage(`请采用三段式教学法辅导我：${content}`)
}
</script>

<template>
  <div class="tutor-page">
    <PageHeader title="智能辅导" description="先诊断卡点，再分步讲解，最后用一个可验证问题确认理解。" />
    <div class="tutor-workspace">
      <section class="question-pane" aria-labelledby="tutor-question-title">
        <img src="/assets/mascot-thinking.png" width="150" height="150" alt="小智析析正在思考辅导方案" />
        <h2 id="tutor-question-title">你卡在哪一步</h2>
        <p>尽量贴出题目、你的思路和出现困惑的位置，辅导会更准确。</p>
        <form @submit.prevent="ask"><div class="field"><label for="tutor-question">学习问题</label><textarea id="tutor-question" v-model="question" maxlength="10000" placeholder="例如：我会求导，但不理解梯度下降为什么沿负梯度更新" :disabled="chatStore.streaming" /></div><button class="primary-button" type="submit" :disabled="!question.trim() || chatStore.streaming"><PaperPlaneRight :size="18" weight="fill" />{{ chatStore.streaming ? '正在辅导' : '开始三段式辅导' }}</button></form>
        <div v-if="chatStore.traces.length" class="tutor-trace"><strong>当前协作</strong><span v-for="trace in chatStore.traces" :key="`${trace.sequence}-${trace.agent}`">{{ trace.content }}</span></div>
        <div v-if="chatStore.error" class="inline-error" role="alert">{{ chatStore.error }}</div>
      </section>

      <section class="answer-pane" aria-label="辅导结果">
        <div class="tutor-tabs" role="tablist" aria-label="辅导呈现方式"><button v-for="(tab, index) in tabs" :id="`tutor-tab-${tab.value}`" :key="tab.value" type="button" role="tab" :aria-controls="`tutor-panel-${tab.value}`" :aria-selected="activeTab === tab.value" :tabindex="activeTab === tab.value ? 0 : -1" :class="{ active: activeTab === tab.value }" @click="selectTab(tab.value)" @keydown="handleTabKeydown($event, index, tabs, selectTab)"><component :is="tab.icon" :size="19" />{{ tab.label }}</button></div>
        <div :id="`tutor-panel-${activeTab}`" class="tab-content" role="tabpanel" :aria-labelledby="`tutor-tab-${activeTab}`" aria-live="polite">
          <div v-if="chatStore.streaming && !lastAnswer?.content" class="answer-skeleton"><img src="/assets/mascot-thinking.png" width="108" height="108" alt="" /><strong>正在检索证据并组织讲解</strong><span class="skeleton-line" /><span class="skeleton-line short" /></div>
          <div v-else-if="!lastAnswer" class="answer-empty"><img src="/assets/mascot-empty.png" width="140" height="140" alt="" /><h2>辅导结果会出现在这里</h2><p>左侧提交问题后，可在文字、图解和视频脚本之间切换。</p></div>
          <MarkdownContent v-else-if="activeTab === 'text'" :source="lastAnswer.content" />
          <MermaidDiagram v-else-if="activeTab === 'diagram' && diagramSource" :source="diagramSource" />
          <div v-else-if="activeTab === 'diagram'" class="answer-empty"><Diagram :size="48" weight="duotone" /><h2>本轮没有结构图解</h2><p>这不是渲染失败，上游回答未提供 Mermaid 图。可以在问题中明确要求图解。</p></div>
          <MarkdownContent v-else-if="activeTab === 'video' && videoScript" :source="videoScript" />
          <div v-else class="answer-empty"><VideoCamera :size="48" weight="duotone" /><h2>本轮没有视频脚本</h2><p>系统不会放置假播放器。需要时可在学习对话中生成包含镜头、旁白和时长的脚本。</p></div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.tutor-workspace { display: grid; min-height: 650px; grid-template-columns: minmax(320px, .72fr) minmax(0, 1.28fr); border: 1px solid var(--color-border); border-radius: var(--radius-card); background: var(--color-surface); }.question-pane { padding: clamp(24px, 4vw, 46px); border-right: 1px solid var(--color-border); background: color-mix(in srgb, var(--color-surface-muted) 58%, var(--color-surface)); }.question-pane > img { margin: -10px auto 4px; object-fit: contain; }.question-pane h2 { margin-bottom: 6px; font-size: 24px; }.question-pane > p { color: var(--color-ink-secondary); }.question-pane form { display: grid; gap: 15px; margin-top: 24px; }.question-pane textarea { min-height: 150px; }.tutor-trace { display: grid; gap: 6px; margin-top: 22px; padding: 14px; border-radius: var(--radius-control); background: var(--color-surface); }.tutor-trace strong { font-size: 13px; }.tutor-trace span { color: var(--color-ink-secondary); font-size: 12px; }.question-pane .inline-error { margin-top: 14px; }
.answer-pane { display: grid; min-width: 0; grid-template-rows: auto minmax(0, 1fr); }.tutor-tabs { display: flex; gap: 5px; padding: 12px 16px; border-bottom: 1px solid var(--color-border); }.tutor-tabs button { display: flex; align-items: center; gap: 7px; min-height: 42px; padding: 8px 13px; border: 0; border-radius: 8px; background: transparent; color: var(--color-ink-secondary); cursor: pointer; }.tutor-tabs button.active { background: var(--color-brand-soft); color: var(--color-brand-action); font-weight: 800; }.tab-content { overflow-y: auto; padding: clamp(22px, 4vw, 44px); }.answer-empty, .answer-skeleton { display: grid; min-height: 430px; place-items: center; align-content: center; text-align: center; }.answer-empty h2 { margin: 10px 0 5px; font-size: 21px; }.answer-empty p { max-width: 48ch; color: var(--color-ink-secondary); }.answer-empty > svg { color: var(--color-brand-action); }.answer-skeleton strong { margin: 5px 0 22px; }.answer-skeleton .skeleton-line { width: min(100%, 520px); margin-bottom: 10px; }.answer-skeleton .short { width: min(72%, 380px); }
@media (max-width: 950px) { .tutor-workspace { grid-template-columns: 1fr; }.question-pane { border-right: 0; border-bottom: 1px solid var(--color-border); }.question-pane > img { width: 110px; height: 110px; }.answer-empty, .answer-skeleton { min-height: 320px; } }
@media (max-width: 560px) { .tutor-tabs { overflow-x: auto; }.tutor-tabs button { white-space: nowrap; } }
</style>
