<script setup lang="ts">
import { computed } from 'vue'
import { RefreshRight, SwitchButton } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { useHealthStore } from '../stores/health'
import { useUserStore } from '../stores/user'

const health = useHealthStore()
const userStore = useUserStore()
const router = useRouter()
const healthDetail = computed(() => health.payload ? JSON.stringify(health.payload, null, 2) : health.error || '等待连接')

async function logout() {
  userStore.logout()
  await router.replace('/login')
}
</script>

<template>
  <main class="workbench">
    <header class="topbar">
      <div class="brand"><img class="brand-mark" src="/assets/mascot-logo.png" alt="小智析析" /><span>知微智学</span></div>
      <div class="topbar-actions">
        <div class="topbar-status"><span class="status-dot"></span>学习工作台</div>
        <div class="user-menu"><span class="username">{{ userStore.user?.username }}</span><el-button circle text aria-label="退出登录" title="退出登录" @click="logout"><el-icon><SwitchButton /></el-icon></el-button></div>
      </div>
    </header>
    <section class="workspace" aria-label="学习工作台">
      <aside class="left-rail animate-fade-up">
        <p class="section-label">学习流程</p>
        <nav class="task-list" aria-label="学习任务"><button class="task active"><span>01</span>诊断与画像</button><button class="task"><span>02</span>知识星图</button><button class="task"><span>03</span>学习路径</button></nav>
        <div class="timeline"><p class="section-label">当前会话</p><div class="timeline-item"><span></span><p>准备建立学习画像</p></div><div class="timeline-item muted"><span></span><p>等待第一条学习输入</p></div></div>
      </aside>
      <section class="center-stage">
        <div class="hero-panel animate-fade-up"><div class="hero-copy"><p class="section-label">小智析析正在待命</p><h1>把每一次学习，变成看得见的<span>星光</span></h1><p>从真实输入开始，建立可演化的学习画像与下一步路径。</p></div><img class="hero-mascot animate-float" src="/assets/mascot-hero.png" alt="漂浮的小智析析" /></div>
        <div class="health-panel animate-scale"><div class="health-heading"><div><span class="health-label">后端服务</span><strong :class="['health-state', health.status]">{{ health.label }}</strong></div><el-button type="primary" :loading="health.loading" @click="health.check"><el-icon><RefreshRight /></el-icon>检查连接</el-button></div><pre class="health-result">{{ healthDetail }}</pre></div>
      </section>
      <aside class="right-rail animate-fade-up">
        <p class="section-label">学习画像</p><div class="profile-summary"><img src="/assets/mascot-chat.png" alt="微笑的小智析析" /><div><strong>等待初始化</strong><p>完成诊断后生成画像</p></div></div>
        <p class="section-label agent-heading">Agent 协作</p><ul class="agent-list"><li><img src="/assets/icon-graph.svg" alt="" /><span>画像构建 Agent</span><em>待命</em></li><li><img src="/assets/icon-path.svg" alt="" /><span>路径规划 Agent</span><em>待命</em></li><li><img src="/assets/icon-document.svg" alt="" /><span>资源生成 Agent</span><em>待命</em></li></ul>
        <div class="challenge"><strong>每日挑战</strong><p>完成第一条学习输入，点亮你的学习星图。</p><div class="progress-track" aria-label="挑战进度 68%"><span></span></div></div>
      </aside>
    </section>
  </main>
</template>

<style scoped>
.topbar-actions,.user-menu{display:flex;align-items:center;gap:12px}.user-menu{min-width:0;padding-left:12px;border-left:1px solid var(--color-border)}.username{max-width:12rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:600}.workspace>*{min-width:0}@media(max-width:720px){.topbar-status{display:none}.username{max-width:8rem}.workspace{overflow-x:hidden}}
</style>
