<script setup>
import {
  PhBookOpenText as BookOpenText,
  PhChatsCircle as ChatsCircle,
  PhHouse as House,
  PhList as List,
  PhMoon as Moon,
  PhPath as Path,
  PhShieldCheck as ShieldCheck,
  PhSignOut as SignOut,
  PhSparkle as Sparkle,
  PhSun as Sun,
  PhX as X,
} from '@phosphor-icons/vue'
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'

import { useAppStore } from '@/stores/app'
import { useUserStore } from '@/stores/user'

const appStore = useAppStore()
const userStore = useUserStore()
const router = useRouter()

const navItems = [
  { to: '/', label: '首页', icon: House },
  { to: '/chat', label: '学习对话', icon: ChatsCircle },
  { to: '/resources', label: '资源库', icon: BookOpenText },
  { to: '/path', label: '学习路径', icon: Path },
  { to: '/tutor', label: '智能辅导', icon: Sparkle },
]

const initials = computed(() => userStore.user?.username?.slice(0, 1) || '学')
const connectionLabel = computed(() => userStore.user ? '后端服务已连接' : '正在检查后端')

onMounted(() => {
  if (userStore.token && !userStore.user) userStore.loadMe().catch(() => router.replace('/login'))
})

function logout() {
  userStore.logout()
  router.replace('/login')
}
</script>

<template>
  <div class="app-shell">
    <aside class="app-sidebar" :class="{ 'is-open': appStore.sidebarOpen }">
      <div class="brand-lockup">
        <img src="/assets/mascot-logo.png" width="44" height="44" alt="" />
        <div><strong>小智析析</strong><span>有证据的个性化学习</span></div>
        <button class="icon-button sidebar-close" type="button" aria-label="关闭导航" @click="appStore.sidebarOpen = false">
          <X :size="20" />
        </button>
      </div>

      <nav aria-label="主导航" class="primary-nav">
        <RouterLink v-for="item in navItems" :key="item.to" :to="item.to" @click="appStore.sidebarOpen = false">
          <component :is="item.icon" :size="21" weight="duotone" />
          <span>{{ item.label }}</span>
        </RouterLink>
        <RouterLink v-if="userStore.user?.is_admin" to="/admin" @click="appStore.sidebarOpen = false">
          <ShieldCheck :size="21" weight="duotone" /><span>管理后台</span>
        </RouterLink>
      </nav>

      <div class="sidebar-foot">
        <div class="identity-badge"><span>{{ initials }}</span><div><strong>{{ userStore.user?.username || '学习者' }}</strong><small>{{ userStore.user?.email || '正在同步身份' }}</small></div></div>
        <button class="quiet-action" type="button" @click="logout"><SignOut :size="18" />退出登录</button>
      </div>
    </aside>

    <div v-if="appStore.sidebarOpen" class="sidebar-backdrop" aria-hidden="true" @click="appStore.sidebarOpen = false" />

    <div class="app-main">
      <header class="topbar">
        <button class="icon-button menu-trigger" type="button" aria-label="打开导航" @click="appStore.sidebarOpen = true"><List :size="22" /></button>
        <div class="system-state"><span class="status-dot" :class="{ checking: !userStore.user }" />{{ connectionLabel }}</div>
        <button class="icon-button" type="button" :aria-label="appStore.theme === 'dark' ? '切换到浅色模式' : '切换到深色模式'" @click="appStore.toggleTheme">
          <Sun v-if="appStore.theme === 'dark'" :size="20" /><Moon v-else :size="20" />
        </button>
      </header>
      <main class="page-stage"><slot /></main>
    </div>
  </div>
</template>
