<script setup lang="ts">
import { ref } from 'vue'
import { Hide, View } from '@element-plus/icons-vue'
import { ElTooltip } from 'element-plus'

withDefaults(defineProps<{
  loading?: boolean
  serverError?: string
}>(), {
  loading: false,
  serverError: '',
})

const emit = defineEmits<{
  submit: [payload: { username: string; password: string; remember: boolean }]
  'focus-change': [focused: boolean]
}>()

const username = ref('')
const password = ref('')
const remember = ref(false)
const passwordVisible = ref(false)
const usernameError = ref('')
const passwordError = ref('')

function submit() {
  usernameError.value = username.value.trim() ? '' : '请输入用户名'
  passwordError.value = password.value ? '' : '请输入密码'
  if (usernameError.value || passwordError.value) return
  emit('submit', { username: username.value.trim(), password: password.value, remember: remember.value })
}

function handleFocusOut(event: FocusEvent) {
  const current = event.currentTarget as HTMLElement
  const next = event.relatedTarget as Node | null
  if (!next || !current.contains(next)) emit('focus-change', false)
}
</script>

<template>
  <form class="login-form" novalidate @submit.prevent="submit" @focusin="emit('focus-change', true)" @focusout="handleFocusOut">
    <fieldset :disabled="loading">
      <div class="auth-field">
        <label for="login-username">用户名</label>
        <input
          id="login-username"
          v-model="username"
          name="username"
          type="text"
          autocomplete="username"
          required
          :disabled="loading"
          :aria-invalid="Boolean(usernameError || serverError)"
          :aria-describedby="usernameError || serverError ? 'login-username-error login-server-error' : undefined"
          @input="usernameError = ''"
        >
        <p v-if="usernameError" id="login-username-error" class="field-error" role="alert">{{ usernameError }}</p>
      </div>

      <div class="auth-field">
        <label for="login-password">密码</label>
        <div class="password-control">
          <input
            id="login-password"
            v-model="password"
            name="password"
            :type="passwordVisible ? 'text' : 'password'"
            autocomplete="current-password"
            required
            :disabled="loading"
            :aria-invalid="Boolean(passwordError || serverError)"
            :aria-describedby="passwordError || serverError ? 'login-password-error login-server-error' : undefined"
            @input="passwordError = ''"
          >
          <ElTooltip :content="passwordVisible ? '隐藏密码' : '显示密码'" placement="top">
            <button
              type="button"
              class="password-toggle"
              data-test="password-toggle"
              :disabled="loading"
              :aria-label="passwordVisible ? '隐藏密码' : '显示密码'"
              :title="passwordVisible ? '隐藏密码' : '显示密码'"
              @click="passwordVisible = !passwordVisible"
            >
              <Hide v-if="passwordVisible" />
              <View v-else />
            </button>
          </ElTooltip>
        </div>
        <p v-if="passwordError" id="login-password-error" class="field-error" role="alert">{{ passwordError }}</p>
      </div>

      <label class="remember-control">
        <input v-model="remember" name="remember" type="checkbox" :disabled="loading">
        <span>保持登录</span>
      </label>

      <p v-if="serverError" id="login-server-error" class="server-error" role="alert">{{ serverError }}</p>
      <button class="login-submit" type="submit" :disabled="loading">
        <span>{{ loading ? '正在登录…' : '登录' }}</span>
      </button>
    </fieldset>
  </form>
</template>
