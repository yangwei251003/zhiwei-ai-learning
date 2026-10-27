<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '../components/product/AppShell.vue'
import http from '../utils/http'
import type { Profile } from '../types/product'

const router = useRouter()
const profile = ref<Profile | null>(null)
const resources = ref(0)
const pathProgress = ref(0)
const filmActive = ref(false)
onMounted(async () => {
  const [p, r] = await Promise.allSettled([http.get<Profile>('/api/profile/current'), http.get('/api/resources/?limit=1')])
  if (p.status === 'fulfilled') profile.value = p.value.data
  if (r.status === 'fulfilled') resources.value = Number(r.value.data.total || 0)
  try {
    const current = await http.get('/api/path/status')
    const steps = current.data.path?.path_data || []
    pathProgress.value = steps.length ? Math.round(steps.filter((item: { status: string }) => item.status === 'completed').length / steps.length * 100) : 0
  } catch { pathProgress.value = 0 }
  window.setTimeout(() => { filmActive.value = true }, 2400)
})
</script>

<template>
  <AppShell>
    <section class="home-hero playground-hero">
      <video class="hero-film" :src="filmActive ? '/assets/editorial/code-review.mp4' : undefined" autoplay muted loop playsinline preload="none" poster="/assets/editorial/code-review-poster.jpg" aria-hidden="true" />
      <div class="hero-film-shade" />
      <div class="hero-copy"><span class="eyebrow">你的个性化学习星图</span><h1>把好奇心，玩成<br /><em>真正的能力。</em></h1><p>为大学生打造的 AI 学习游乐场：一句话生成讲解、资源和专属路径，边探索，边看见成长。</p><button class="primary-button glow" @click="router.push('/chat')">开始今天的探索 <span>→</span></button></div>
      <div class="hero-sticker"><img src="/assets/mascot-hero.webp" alt="小智析析邀请你开始学习" /><span>5 个 Agent<br />正在组队</span></div>
    </section>
    <section class="metric-strip">
      <article><span>画像专业</span><strong>{{ profile?.major || '待探索' }}</strong><small>随对话持续更新</small></article>
      <article><span>已生成资源</span><strong>{{ resources }}</strong><small>文档、导图与练习</small></article>
      <article><span>路径进度</span><strong>{{ pathProgress }}%</strong><small>每一步都算数</small></article>
    </section>
    <section class="section-block"><div class="section-heading"><div><span class="eyebrow">三步形成学习闭环</span><h2>从一句问题，到一条自己的路</h2></div></div><div class="feature-grid"><article><b>01</b><img src="/assets/icon-graph.svg" alt="" loading="lazy" /><h3>先理解你</h3><p>从专业、目标和偏好建立可演化画像。</p></article><article><b>02</b><img src="/assets/icon-document.svg" alt="" loading="lazy" /><h3>再创造资源</h3><p>一次生成讲解、导图、测验与代码案例。</p></article><article><b>03</b><img src="/assets/icon-path.svg" alt="" loading="lazy" /><h3>持续走下去</h3><p>把目标拆成有进度、有反馈的学习路径。</p></article></div></section>
    <section class="editorial-band"><img src="/assets/editorial/electronics-class.jpg" alt="学生在课堂中动手学习电子技术" loading="lazy" /><div><span class="eyebrow">专业不是边界，是起点</span><h2>把课堂知识接到真实世界</h2><p>无论电气、计算机还是交叉学科，画像 Agent 都会用你的专业语境组织例子，让抽象知识变得可感、可练、可迁移。</p><button class="secondary-button" @click="router.push('/tutor')">问问智能辅导 →</button></div></section>
  </AppShell>
</template>
