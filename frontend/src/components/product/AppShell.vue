<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useUserStore } from '../../stores/user'

const route = useRoute()
const router = useRouter()
const user = useUserStore()
const mobileOpen = ref(false)
const dark = ref(false)
const nav = [
  ['首页', '/workbench', '⌂'], ['对话', '/chat', '✦'], ['资源库', '/resources', '▦'],
  ['学习路径', '/path', '⌁'], ['智能辅导', '/tutor', '◈'], ['管理后台', '/admin', '⚙'],
] as const

function applyTheme(value: boolean) {
  dark.value = value
  document.documentElement.classList.toggle('dark', value)
  localStorage.setItem('zhiwei.theme', value ? 'dark' : 'light')
}

function logout() {
  user.logout()
  router.replace('/login')
}

onMounted(() => applyTheme(localStorage.getItem('zhiwei.theme') === 'dark'))
</script>

<template>
  <div :class="['product-shell', `route-${String(route.name || 'page')}`]">
    <aside :class="['product-sidebar', { open: mobileOpen }]">
      <RouterLink class="product-logo" to="/workbench" @click="mobileOpen = false">
        <img src="/assets/mascot-logo.webp" alt="小智析析" /><span><strong>知微智学</strong><small>AI 学习星图</small></span>
      </RouterLink>
      <nav aria-label="主导航">
        <RouterLink v-for="item in nav" :key="item[1]" :to="item[1]" :class="{ active: route.path === item[1] }" @click="mobileOpen = false">
          <span aria-hidden="true">{{ item[2] }}</span>{{ item[0] }}
        </RouterLink>
      </nav>
      <div class="sidebar-agent"><span class="live-dot" />5 个 Agent 在线<small>随时为你协作</small></div>
    </aside>
    <div class="product-main">
      <header class="product-topbar">
        <button class="icon-button mobile-menu" aria-label="打开导航" @click="mobileOpen = !mobileOpen">☰</button>
        <div><strong>{{ route.meta.title || '学习工作台' }}</strong><small>让每一步学习都有依据</small></div>
        <div class="topbar-tools">
          <button class="icon-button" :aria-label="dark ? '切换亮色模式' : '切换暗色模式'" @click="applyTheme(!dark)">{{ dark ? '☀' : '☾' }}</button>
          <span class="user-chip"><img src="/assets/mascot-chat.png" alt="" loading="lazy" />{{ user.user?.username || '学习者' }}</span>
          <button class="text-button" aria-label="退出登录" @click="logout">退出</button>
        </div>
      </header>
      <main class="page-stage animate-page-enter"><slot /></main>
    </div>
    <button v-if="mobileOpen" class="sidebar-backdrop" aria-label="关闭导航" @click="mobileOpen = false" />
  </div>
</template>
