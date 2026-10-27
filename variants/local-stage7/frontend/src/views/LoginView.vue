<script setup>
import { computed, reactive } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AuthLayout from '@/components/AuthLayout.vue'
import { useUserStore } from '@/stores/user'

const form = reactive({ email: '', password: '' })
const touched = reactive({ email: false, password: false })
const userStore = useUserStore()
const router = useRouter()
const route = useRoute()
const emailError = computed(() => touched.email && !/^\S+@\S+\.\S+$/.test(form.email) ? '请输入有效邮箱' : '')
const passwordError = computed(() => touched.password && form.password.length < 8 ? '密码至少 8 位' : '')
const invalid = computed(() => !form.email || !form.password || Boolean(emailError.value || passwordError.value))

async function submit() {
  touched.email = touched.password = true
  if (invalid.value) return
  try {
    await userStore.login(form)
    await router.replace(typeof route.query.redirect === 'string' ? route.query.redirect : '/')
  } catch { /* store exposes the real API error */ }
}
</script>

<template>
  <AuthLayout mode="login">
    <div class="auth-heading"><p>欢迎回来</p><h1>继续你的学习旅程</h1><span>登录后继续上次对话、资源和学习路径。</span></div>
    <form class="auth-form" novalidate @submit.prevent="submit">
      <div class="field"><label for="login-email">邮箱</label><input id="login-email" v-model.trim="form.email" type="email" autocomplete="email" placeholder="name@example.com" @blur="touched.email = true" /><span v-if="emailError" class="field-error">{{ emailError }}</span></div>
      <div class="field"><label for="login-password">密码</label><input id="login-password" v-model="form.password" type="password" autocomplete="current-password" placeholder="输入至少 8 位密码" @blur="touched.password = true" /><span v-if="passwordError" class="field-error">{{ passwordError }}</span></div>
      <div v-if="userStore.error" class="inline-error" role="alert">{{ userStore.error }}</div>
      <button class="primary-button auth-submit" type="submit" :disabled="invalid || userStore.loading">{{ userStore.loading ? '正在验证' : '登录' }}</button>
    </form>
    <p class="auth-switch">还没有账号？<RouterLink to="/register">建立学习画像</RouterLink></p>
  </AuthLayout>
</template>

<style scoped>
.auth-heading { margin-bottom: 30px; }
.auth-heading > p { margin-bottom: 6px; color: var(--color-brand-action); font-weight: 800; }
.auth-heading h1 { margin-bottom: 10px; font-size: 34px; line-height: 1.2; }
.auth-heading span { color: var(--color-ink-secondary); }
.auth-form { display: grid; gap: 19px; }
.auth-submit { width: 100%; margin-top: 4px; }
.auth-switch { margin: 24px 0 0; color: var(--color-ink-secondary); text-align: center; }
.auth-switch a { color: var(--color-brand-action); font-weight: 800; }
</style>
