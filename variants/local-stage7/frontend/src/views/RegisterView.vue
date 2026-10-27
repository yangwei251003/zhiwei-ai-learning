<script setup>
import { computed, reactive } from 'vue'
import { useRouter } from 'vue-router'

import AuthLayout from '@/components/AuthLayout.vue'
import { useUserStore } from '@/stores/user'

const form = reactive({ username: '', email: '', password: '', major: '', learning_style: '' })
const userStore = useUserStore()
const router = useRouter()
const valid = computed(() => form.username.length >= 2 && /^\S+@\S+\.\S+$/.test(form.email) && form.password.length >= 8 && form.major.length >= 2 && form.learning_style.length >= 2)

async function submit() {
  if (!valid.value) return
  try { await userStore.register(form); await router.replace('/') } catch { /* visible store error */ }
}
</script>

<template>
  <AuthLayout mode="register">
    <div class="auth-heading"><p>从你开始</p><h1>建立你的学习画像</h1><span>先回答两个学习问题，画像会在后续对话中持续完善。</span></div>
    <form class="register-form" @submit.prevent="submit">
      <div class="form-row">
        <div class="field"><label for="register-name">用户名</label><input id="register-name" v-model.trim="form.username" autocomplete="username" placeholder="你的称呼" minlength="2" required /></div>
        <div class="field"><label for="register-email">邮箱</label><input id="register-email" v-model.trim="form.email" type="email" autocomplete="email" placeholder="name@example.com" required /></div>
      </div>
      <div class="field"><label for="register-password">密码</label><input id="register-password" v-model="form.password" type="password" autocomplete="new-password" placeholder="至少 8 位，不超过 72 字节" minlength="8" required /></div>
      <div class="field"><label for="register-major">专业方向</label><input id="register-major" v-model.trim="form.major" placeholder="例如：计算机科学与技术" minlength="2" required /></div>
      <div class="field"><label for="register-style">学习方式</label><select id="register-style" v-model="form.learning_style" required><option value="" disabled>选择更接近你的方式</option><option>先看例子再理解概念</option><option>先理解原理再动手</option><option>通过练习与反馈掌握</option><option>偏好图解与结构梳理</option></select></div>
      <div v-if="userStore.error" class="inline-error" role="alert">{{ userStore.error }}</div>
      <button class="primary-button auth-submit" type="submit" :disabled="!valid || userStore.loading">{{ userStore.loading ? '正在建立画像' : '创建账号并开始' }}</button>
    </form>
    <p class="auth-switch">已有账号？<RouterLink to="/login">返回登录</RouterLink></p>
  </AuthLayout>
</template>

<style scoped>
.auth-heading { margin-bottom: 24px; }
.auth-heading > p { margin-bottom: 6px; color: var(--color-brand-action); font-weight: 800; }
.auth-heading h1 { margin-bottom: 10px; font-size: 34px; line-height: 1.2; }
.auth-heading span { color: var(--color-ink-secondary); }
.register-form { display: grid; gap: 15px; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.auth-submit { width: 100%; margin-top: 4px; }
.auth-switch { margin: 20px 0 0; color: var(--color-ink-secondary); text-align: center; }
.auth-switch a { color: var(--color-brand-action); font-weight: 800; }
@media (max-width: 560px) { .form-row { grid-template-columns: 1fr; } }
</style>
