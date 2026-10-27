<script setup>
import { PhArrowRight as ArrowRight, PhBookOpenText as BookOpenText, PhCheckCircle as CheckCircle, PhChatsCircle as ChatsCircle, PhPath as Path, PhPulse as Pulse } from '@phosphor-icons/vue'
import { computed, onMounted, ref } from 'vue'

import StatePanel from '@/components/StatePanel.vue'
import { getAchievements, getAgentStatus } from '@/api/system'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const agents = ref([])
const achievements = ref([])
const loading = ref(true)
const error = ref('')
const completedRuns = computed(() => agents.value.reduce((sum, agent) => sum + agent.run_count, 0))
const unlocked = computed(() => achievements.value.filter((item) => item.unlocked).length)

async function loadOverview() {
  loading.value = true; error.value = ''
  try { [agents.value, achievements.value] = await Promise.all([getAgentStatus(), getAchievements()]) }
  catch (reason) { error.value = reason.message }
  finally { loading.value = false }
}
onMounted(loadOverview)
</script>

<template>
  <div class="home-page">
    <section class="home-hero">
      <div class="hero-copy">
        <p class="hero-greeting">{{ userStore.user?.username ? `${userStore.user.username}，欢迎回来` : '欢迎回到学习舱' }}</p>
        <h1>今天从哪里继续</h1>
        <p>从一个问题开始，小智析析会检索证据、更新画像，并把回答沉淀成资源与路径。</p>
        <div class="hero-actions"><RouterLink class="primary-button" to="/chat">开始学习对话<ArrowRight :size="18" /></RouterLink><RouterLink class="secondary-button" to="/path">查看学习路径</RouterLink></div>
      </div>
      <div class="hero-visual"><img src="/assets/mascot-hero.png" width="800" height="600" alt="小智析析在学习舱中分析知识" fetchpriority="high" /><div class="evidence-float"><CheckCircle :size="22" weight="fill" /><div><strong>证据先于答案</strong><span>每轮回答先检索知识库</span></div></div></div>
    </section>

    <StatePanel v-if="loading" state="loading" />
    <StatePanel v-else-if="error" state="error" title="学习概览暂未同步" :message="error" action-label="重新连接" @action="loadOverview" />
    <template v-else>
      <section class="overview-strip" aria-label="学习概览">
        <div><Pulse :size="24" weight="duotone" /><span>Agent 累计运行</span><strong>{{ completedRuns }}</strong></div>
        <div><CheckCircle :size="24" weight="duotone" /><span>已解锁成就</span><strong>{{ unlocked }} / {{ achievements.length }}</strong></div>
        <div><BookOpenText :size="24" weight="duotone" /><span>可用智能体</span><strong>{{ agents.filter(a => a.enabled).length }} / {{ agents.length }}</strong></div>
      </section>

      <section class="learning-loop">
        <div class="section-copy"><h2>一次提问，走完学习闭环</h2><p>不是把答案留在聊天框里，而是让画像、资源和路径继续为下一次学习服务。</p></div>
        <ol>
          <li><ChatsCircle :size="25" /><div><strong>提出真实问题</strong><span>说明目标、基础或卡住的位置</span></div></li>
          <li><Pulse :size="25" /><div><strong>观察协作过程</strong><span>看见检索、画像与教学 Agent 的工作状态</span></div></li>
          <li><BookOpenText :size="25" /><div><strong>沉淀学习资源</strong><span>把讲解、图解、练习与代码保存到资源库</span></div></li>
          <li><Path :size="25" /><div><strong>推进学习路径</strong><span>把当前理解转化为明确的下一步行动</span></div></li>
        </ol>
      </section>

      <section class="agent-board"><div class="section-copy"><h2>多智能体协作</h2><p>每个角色只承担清晰职责，状态和调用次数来自真实后端。</p></div><div class="agent-list"><article v-for="agent in agents" :key="agent.name"><span :class="['agent-state', agent.status]">{{ agent.enabled ? (agent.status === 'running' ? '工作中' : '待命') : '已停用' }}</span><strong>{{ agent.label }}</strong><small>已运行 {{ agent.run_count }} 次<span v-if="agent.last_duration_ms"> · 最近 {{ agent.last_duration_ms }} ms</span></small></article></div></section>
    </template>
  </div>
</template>

<style scoped>
.home-page { display: grid; gap: 46px; }
.home-hero { position: relative; display: grid; overflow: hidden; min-height: 500px; grid-template-columns: minmax(0, .92fr) minmax(420px, 1.08fr); align-items: center; border-radius: var(--radius-card); background: linear-gradient(135deg, #131d3b, #252b67 70%, #4f46a5); color: #fff; }
.hero-copy { position: relative; z-index: 2; padding: clamp(34px, 5vw, 72px); }
.hero-greeting { margin-bottom: 13px; color: #cdd5ff; font-weight: 800; }
.hero-copy h1 { max-width: 9ch; margin-bottom: 18px; font-size: clamp(44px, 5vw, 70px); line-height: 1.02; letter-spacing: -.035em; }
.hero-copy > p:not(.hero-greeting) { max-width: 40ch; color: #e1e5f5; }
.hero-actions { display: flex; flex-wrap: wrap; gap: 11px; margin-top: 28px; }
.hero-actions .secondary-button { border-color: rgb(255 255 255 / .32); background: rgb(255 255 255 / .1); color: #fff; backdrop-filter: blur(8px); }
.hero-visual { position: relative; align-self: end; min-height: 450px; }
.hero-visual > img { position: absolute; right: -3%; bottom: -9%; width: min(100%, 650px); object-fit: contain; filter: drop-shadow(0 8px 8px rgb(4 8 27 / .28)); animation: float 5.5s ease-in-out infinite; }
.evidence-float { position: absolute; right: 8%; bottom: 9%; display: flex; align-items: center; gap: 10px; padding: 13px 16px; border: 1px solid rgb(255 255 255 / .25); border-radius: var(--radius-control); background: rgb(8 14 39 / .68); backdrop-filter: blur(12px); }
.evidence-float svg { color: #6ee7b7; }
.evidence-float div { display: grid; }.evidence-float span { color: #d9dff4; font-size: 12px; }
.overview-strip { display: grid; grid-template-columns: repeat(3, 1fr); border-block: 1px solid var(--color-border); }
.overview-strip > div { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 12px; padding: 22px; }.overview-strip > div + div { border-left: 1px solid var(--color-border); }
.overview-strip svg { color: var(--color-brand-action); }.overview-strip span { color: var(--color-ink-secondary); }.overview-strip strong { font: 800 22px/1 var(--font-mono); }
.section-copy { max-width: 680px; }.section-copy h2 { margin-bottom: 8px; font-size: 27px; }.section-copy p { color: var(--color-ink-secondary); }
.learning-loop { display: grid; grid-template-columns: .7fr 1.3fr; gap: 7vw; align-items: start; }
.learning-loop ol { display: grid; margin: 0; padding: 0; list-style: none; counter-reset: loop; }
.learning-loop li { display: grid; grid-template-columns: 44px 1fr; gap: 15px; padding: 20px 0; border-bottom: 1px solid var(--color-border); counter-increment: loop; }
.learning-loop li svg { padding: 9px; border-radius: 50%; background: var(--color-brand-soft); color: var(--color-brand-action); box-sizing: content-box; }
.learning-loop li div { display: grid; }.learning-loop li span { color: var(--color-ink-secondary); font-size: 14px; }
.agent-board { display: grid; gap: 18px; }.agent-list { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); border-top: 1px solid var(--color-border); }
.agent-list article { display: grid; gap: 4px; padding: 19px 16px; border-bottom: 1px solid var(--color-border); }.agent-list small { color: var(--color-ink-secondary); }.agent-state { width: max-content; font-size: 12px; font-weight: 800; }.agent-state.running { color: var(--color-success); animation: breathe 1.4s ease-in-out infinite; }
@media (max-width: 1000px) { .home-hero { grid-template-columns: 1fr 420px; }.hero-visual { min-height: 390px; }.learning-loop { grid-template-columns: 1fr; gap: 16px; } }
@media (max-width: 760px) { .home-page { gap: 32px; }.home-hero { min-height: auto; grid-template-columns: 1fr; }.hero-copy h1 { font-size: 43px; }.hero-visual { min-height: 290px; }.evidence-float { right: 16px; bottom: 16px; }.overview-strip { grid-template-columns: 1fr; }.overview-strip > div + div { border-left: 0; border-top: 1px solid var(--color-border); } }
@media (prefers-reduced-motion: reduce) { .hero-visual > img, .agent-state.running { animation: none; } }
</style>
