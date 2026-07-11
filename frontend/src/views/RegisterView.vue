<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import AuthShell from '../components/auth/AuthShell.vue'
import RegisterForm, { type RegistrationInput } from '../components/auth/RegisterForm.vue'
import { useUserStore } from '../stores/user'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
const retrying = ref(false)
const serverError = ref('')
const focused = ref(false)
const celebrating = ref(false)
const pendingProfile = ref<Pick<RegistrationInput, 'major' | 'learningStyle'>>()
const profilePending = ref(false)
const welcome = '欢迎加入！我是小智析析，准备好一起学习了吗？'

function message(error: unknown, fallback: string) {
  return error instanceof Error && error.message.trim() ? error.message : fallback
}
async function celebrate() {
  profilePending.value = false
  celebrating.value = true
  await new Promise((resolve) => setTimeout(resolve, 420))
  await router.replace('/workbench')
}
async function handleSubmit(payload: RegistrationInput) {
  if (loading.value || retrying.value || celebrating.value || profilePending.value) return
  loading.value = true; serverError.value = ''; pendingProfile.value = { major: payload.major, learningStyle: payload.learningStyle }
  try {
    const result = await userStore.register({ username: payload.username, password: payload.password, major: payload.major, cognitive_style: payload.learningStyle } as Parameters<typeof userStore.register>[0])
    if (result.profileSaved) await celebrate()
    else profilePending.value = true
  } catch (error) { serverError.value = message(error, '注册失败，请稍后重试') }
  finally { loading.value = false }
}
async function retryProfile() {
  if (retrying.value || !pendingProfile.value) return
  retrying.value = true; serverError.value = ''
  try {
    await userStore.saveProfile(pendingProfile.value.major, pendingProfile.value.learningStyle)
    await celebrate()
  } catch (error) { serverError.value = message(error, '画像资料保存失败，请重试') }
  finally { retrying.value = false }
}
</script>

<template>
  <AuthShell :focused="focused || celebrating" :celebrating="celebrating">
    <section class="login-panel register-panel">
      <div class="login-heading">
        <p class="login-eyebrow">你的个性化学习起点</p>
        <h2>创建学习账户</h2>
        <p>告诉我们一点你的学习偏好，让每次推荐都更懂你</p>
      </div>
      <template v-if="profilePending">
        <div class="profile-pending" role="status">
          <strong>账户已创建，画像资料暂未保存</strong>
          <p>你的专业与学习风格已保留，可以直接重试。</p>
          <p v-if="serverError" class="server-error" role="alert">{{ serverError }}</p>
          <button data-test="retry-profile" class="login-submit" type="button" :disabled="retrying" @click="retryProfile">{{ retrying ? '正在保存…' : '重试保存画像' }}</button>
        </div>
      </template>
      <template v-else>
        <RegisterForm :loading="loading" :server-error="serverError" @submit="handleSubmit" @focus-change="focused = $event" />
        <p class="auth-switch">已有账户？<RouterLink to="/login">登录</RouterLink></p>
      </template>
      <div v-if="celebrating" class="success-curtain" role="status" aria-live="polite"><strong>{{ welcome }}</strong><span>正在进入你的学习工作台</span></div>
    </section>
    <template #footer>创建账户即表示你同意以安全方式使用知微智学服务</template>
  </AuthShell>
</template>
