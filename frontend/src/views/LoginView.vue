<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import AuthShell from '../components/auth/AuthShell.vue'
import LoginForm from '../components/auth/LoginForm.vue'
import { useUserStore } from '../stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
const serverError = ref('')
const shakeKey = ref(0)
const focused = ref(false)
const celebrating = ref(false)

function safeRedirect(value: unknown): string {
  if (
    typeof value !== 'string'
    || !value.startsWith('/')
    || value.startsWith('//')
    || value.includes('\\')
    || /^\/[a-z][a-z\d+.-]*:/i.test(value)
  ) return '/workbench'
  return value
}

function errorMessage(error: unknown): string {
  if (error instanceof Error && error.message.trim()) return error.message
  if (typeof error === 'object' && error && 'message' in error && typeof error.message === 'string') return error.message
  return '登录失败，请检查用户名和密码后重试'
}

async function handleSubmit(payload: { username: string; password: string; remember: boolean }) {
  if (loading.value || celebrating.value) return
  loading.value = true
  serverError.value = ''
  try {
    await userStore.login({ username: payload.username, password: payload.password })
    celebrating.value = true
    await new Promise((resolve) => setTimeout(resolve, 420))
    await router.replace(safeRedirect(route.query.redirect))
  } catch (error) {
    serverError.value = errorMessage(error)
    shakeKey.value += 1
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <AuthShell :focused="focused || celebrating" :celebrating="celebrating">
    <section
      :key="shakeKey"
      class="login-panel"
      :class="{ 'auth-shake': serverError }"
      data-test="login-panel"
      :data-shake-key="shakeKey"
    >
      <div class="login-heading">
        <p class="login-eyebrow">智能学习账户</p>
        <h2>欢迎回来，学习伙伴</h2>
        <p>让 AI 读懂你，给你最好的学习资源</p>
      </div>
      <LoginForm
        :loading="loading"
        :server-error="serverError"
        @submit="handleSubmit"
        @focus-change="focused = $event"
      />
      <p class="auth-switch">还没有账户？<RouterLink to="/register">创建账户</RouterLink></p>
      <div v-if="celebrating" class="success-curtain" role="status" aria-live="polite">
        <strong>登录成功</strong>
        <span>正在进入你的学习工作台</span>
      </div>
    </section>
    <template #footer>继续即表示你同意以安全方式使用知微智学服务</template>
  </AuthShell>
</template>
