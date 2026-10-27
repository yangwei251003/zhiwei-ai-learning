<script setup>
import { PhCheck as Check, PhCircle as Circle, PhFlag as Flag, PhLock as Lock, PhPlay as Play, PhSparkle as Sparkle } from '@phosphor-icons/vue'
import { computed, onMounted, ref } from 'vue'

import PageHeader from '@/components/PageHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import { generatePath, getPath, updatePathProgress } from '@/api/path'

const path = ref(null)
const goal = ref('')
const loading = ref(false)
const savingStep = ref(null)
const error = ref('')
const progressLabel = computed(() => `${Math.round(path.value?.progress || 0)}%`)

async function restore() {
  const id = localStorage.getItem('xzxx-path-id')
  if (!id) return
  loading.value = true
  try { path.value = await getPath(id) }
  catch (reason) { error.value = reason.message; localStorage.removeItem('xzxx-path-id') }
  finally { loading.value = false }
}

async function createPath() {
  if (goal.value.trim().length < 2) return
  loading.value = true; error.value = ''
  try { path.value = await generatePath(goal.value.trim()); localStorage.setItem('xzxx-path-id', String(path.value.id)) }
  catch (reason) { error.value = reason.message }
  finally { loading.value = false }
}

async function completeStep(step) {
  savingStep.value = step.id; error.value = ''
  try { path.value = await updatePathProgress(path.value.id, step.id, 100) }
  catch (reason) { error.value = reason.message }
  finally { savingStep.value = null }
}

function statusLabel(step) {
  if (step.status === 'completed') return '已完成'
  if (step.status === 'in_progress') return '进行中'
  return '待开始'
}
onMounted(restore)
</script>

<template>
  <div class="path-page">
    <PageHeader title="个性化学习路径" description="路径由画像、目标和知识证据共同生成，进度变化会保存到真实账户。">
      <template #actions><button v-if="path" class="secondary-button" type="button" :disabled="loading" @click="path = null; goal = ''"><Sparkle :size="18" />规划新路径</button></template>
    </PageHeader>

    <StatePanel v-if="loading && !path" state="loading" />
    <section v-else-if="!path" class="path-onboarding">
      <div class="path-prompt"><img src="/assets/mascot-thinking.png" width="210" height="210" alt="小智析析正在思考学习计划" /><div><h2>先说清楚你想抵达哪里</h2><p>目标越具体，路径越能匹配你的基础、时间与学习方式。</p></div></div>
      <form @submit.prevent="createPath"><div class="field"><label for="path-goal">学习目标</label><textarea id="path-goal" v-model="goal" maxlength="500" placeholder="例如：两周内掌握数据结构中的树与图，每天学习 50 分钟，并能独立完成基础算法题" /></div><div v-if="error" class="inline-error" role="alert">{{ error }}</div><button class="primary-button" type="submit" :disabled="goal.trim().length < 2 || loading">{{ loading ? '正在规划' : '生成学习路径' }}</button></form>
    </section>

    <template v-else>
      <section class="path-summary">
        <div class="progress-ring" :style="{ '--progress': `${path.progress * 3.6}deg` }"><div><strong>{{ progressLabel }}</strong><span>整体进度</span></div></div>
        <div class="path-summary-copy"><span>{{ path.status === 'completed' ? '路径已完成' : '当前学习计划' }}</span><h2>{{ path.title }}</h2><p>{{ path.goal }}</p></div>
        <div class="next-action"><Flag :size="24" weight="duotone" /><div><span>下一步行动</span><strong>{{ path.steps.find(step => step.status !== 'completed')?.title || '回顾并巩固全部内容' }}</strong></div></div>
      </section>

      <div v-if="error" class="inline-error path-error" role="alert">{{ error }}</div>
      <section class="timeline-section" aria-label="学习步骤">
        <article v-for="(step, index) in path.steps" :key="step.id" :class="['timeline-step', `status-${step.status}`]">
          <div class="timeline-marker"><Check v-if="step.status === 'completed'" :size="20" weight="bold" /><Play v-else-if="step.status === 'in_progress' || index === path.steps.findIndex(item => item.status !== 'completed')" :size="18" weight="fill" /><Lock v-else-if="index > path.steps.findIndex(item => item.status !== 'completed') + 1" :size="17" /><Circle v-else :size="18" /></div>
          <div class="step-content"><div class="step-top"><span>第 {{ step.position }} 步 · {{ statusLabel(step) }}</span><strong>{{ Math.round(step.progress) }}%</strong></div><h2>{{ step.title }}</h2><p>{{ step.description }}</p><button v-if="step.status !== 'completed'" class="secondary-button" type="button" :disabled="savingStep === step.id" @click="completeStep(step)">{{ savingStep === step.id ? '正在保存' : '标记完成' }}</button><span v-else class="completed-label"><Check :size="17" weight="bold" />此步骤已完成</span></div>
        </article>
      </section>
    </template>
  </div>
</template>

<style scoped>
.path-onboarding { display: grid; max-width: 980px; margin: 7vh auto 0; grid-template-columns: .85fr 1.15fr; gap: 7vw; align-items: center; }.path-prompt { text-align: center; }.path-prompt img { margin: 0 auto; object-fit: contain; }.path-prompt h2 { margin-bottom: 7px; font-size: 25px; }.path-prompt p { color: var(--color-ink-secondary); }.path-onboarding form { display: grid; gap: 16px; padding: 24px; border: 1px solid var(--color-border); border-radius: var(--radius-card); background: var(--color-surface); }
.path-summary { display: grid; grid-template-columns: auto minmax(0, 1fr) minmax(240px, .65fr); gap: 28px; align-items: center; padding: 26px 0 30px; border-block: 1px solid var(--color-border); }.progress-ring { display: grid; width: 122px; height: 122px; place-items: center; border-radius: 50%; background: conic-gradient(var(--color-brand-action) var(--progress), var(--color-surface-muted) 0); }.progress-ring::before { position: absolute; width: 92px; height: 92px; border-radius: 50%; background: var(--color-canvas); content: ''; }.progress-ring div { position: relative; display: grid; text-align: center; }.progress-ring strong { font: 800 24px/1.2 var(--font-mono); }.progress-ring span { color: var(--color-ink-secondary); font-size: 11px; }.path-summary-copy > span { color: var(--color-brand-action); font-size: 13px; font-weight: 800; }.path-summary-copy h2 { margin: 4px 0 7px; font-size: 25px; }.path-summary-copy p { margin: 0; color: var(--color-ink-secondary); }.next-action { display: flex; gap: 11px; padding: 16px; border-radius: var(--radius-control); background: var(--color-brand-soft); color: var(--color-brand-action); }.next-action div { display: grid; }.next-action span { font-size: 12px; }.next-action strong { color: var(--color-ink); font-size: 14px; }.path-error { margin-top: 20px; }
.timeline-section { max-width: 900px; margin: 42px auto 0; }.timeline-step { position: relative; display: grid; grid-template-columns: 48px minmax(0, 1fr); gap: 18px; padding-bottom: 34px; }.timeline-step:not(:last-child)::before { position: absolute; top: 42px; bottom: 0; left: 23px; width: 1px; background: var(--color-border); content: ''; }.timeline-marker { position: relative; z-index: 1; display: grid; width: 46px; height: 46px; place-items: center; border: 1px solid var(--color-border); border-radius: 50%; background: var(--color-surface); color: var(--color-ink-secondary); }.status-completed .timeline-marker { border-color: var(--color-success); background: var(--color-success); color: #fff; }.status-in_progress .timeline-marker { border-color: var(--color-brand-action); background: var(--color-brand-action); color: #fff; animation: breathe 1.5s ease-in-out infinite; }.step-content { padding: 3px 0 10px; }.step-top { display: flex; justify-content: space-between; gap: 12px; color: var(--color-ink-secondary); font-size: 12px; }.step-content h2 { margin: 4px 0 6px; font-size: 20px; }.step-content p { max-width: 68ch; margin-bottom: 14px; color: var(--color-ink-secondary); }.completed-label { display: flex; align-items: center; gap: 6px; color: var(--color-success); font-size: 13px; font-weight: 800; }
@media (max-width: 850px) { .path-summary { grid-template-columns: auto 1fr; }.next-action { grid-column: 1 / -1; }.path-onboarding { grid-template-columns: 1fr; gap: 18px; margin-top: 0; }.path-prompt img { width: 150px; height: 150px; } }
@media (max-width: 560px) { .path-summary { grid-template-columns: 1fr; }.progress-ring { width: 105px; height: 105px; }.progress-ring::before { width: 78px; height: 78px; }.timeline-step { grid-template-columns: 38px 1fr; gap: 12px; }.timeline-marker { width: 38px; height: 38px; }.timeline-step:not(:last-child)::before { top: 36px; left: 19px; } }
@media (prefers-reduced-motion: reduce) { .status-in_progress .timeline-marker { animation: none; } }
</style>
