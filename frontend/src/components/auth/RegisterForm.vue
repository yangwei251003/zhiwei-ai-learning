<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { Hide, View } from '@element-plus/icons-vue'
import { ElTooltip } from 'element-plus'
import type { LearningStyle } from '../../types/auth'

export interface RegistrationInput {
  username: string
  password: string
  major: string
  learningStyle?: LearningStyle
}

const props = withDefaults(defineProps<{ loading?: boolean; serverError?: string }>(), {
  loading: false,
  serverError: '',
})
const emit = defineEmits<{ submit: [payload: RegistrationInput]; 'focus-change': [focused: boolean] }>()

const majors = ['计算机科学与技术', '软件工程', '人工智能', '数据科学与大数据技术', '网络工程', '信息安全', '电子信息工程', '自动化', '数学与应用数学', '其他']
const styles: { value: LearningStyle; label: string }[] = [
  { value: 'visual', label: '视觉型' }, { value: 'auditory', label: '听觉型' },
  { value: 'hands_on', label: '动手型' }, { value: 'theoretical', label: '理论型' },
]
const username = ref('')
const password = ref('')
const major = ref('')
const learningStyle = ref<LearningStyle>()
const passwordVisible = ref(false)
const open = ref(false)
const activeIndex = ref(-1)
const usernameError = ref('')
const passwordError = ref('')
const majorError = ref('')
const root = ref<HTMLElement>()
const filteredMajors = computed(() => majors.filter((item) => item.includes(major.value.trim())))
const activeId = computed(() => open.value && activeIndex.value >= 0 ? `register-major-option-${activeIndex.value}` : undefined)

function describedBy(error: string, ownId: string) {
  const ids = [error ? ownId : '', props.serverError ? 'register-server-error' : ''].filter(Boolean)
  return ids.length ? ids.join(' ') : undefined
}
function updateMajor() { majorError.value = ''; open.value = true; activeIndex.value = -1 }
function choose(item: string) { major.value = item; majorError.value = ''; open.value = false; activeIndex.value = -1 }
function keydown(event: KeyboardEvent) {
  if (event.key === 'Escape') { open.value = false; activeIndex.value = -1; return }
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault(); open.value = true
    const count = filteredMajors.value.length
    if (!count) return
    activeIndex.value = event.key === 'ArrowDown'
      ? (activeIndex.value + 1) % count
      : (activeIndex.value <= 0 ? count - 1 : activeIndex.value - 1)
  } else if (event.key === 'Enter' && open.value && activeIndex.value >= 0) {
    event.preventDefault(); choose(filteredMajors.value[activeIndex.value])
  }
}
function submit() {
  usernameError.value = username.value.trim() ? '' : '请输入用户名'
  passwordError.value = password.value.length >= 8 ? '' : '密码至少需要 8 个字符'
  majorError.value = major.value.trim() ? '' : '请输入专业'
  if (usernameError.value || passwordError.value || majorError.value) return
  emit('submit', {
    username: username.value.trim(), password: password.value, major: major.value.trim(),
    ...(learningStyle.value ? { learningStyle: learningStyle.value } : {}),
  })
}
function focusOut(event: FocusEvent) {
  const next = event.relatedTarget as Node | null
  if (!next || !(event.currentTarget as HTMLElement).contains(next)) emit('focus-change', false)
}
function outside(event: MouseEvent) { if (root.value && !root.value.contains(event.target as Node)) open.value = false }
onMounted(() => document.addEventListener('mousedown', outside))
onBeforeUnmount(() => document.removeEventListener('mousedown', outside))
</script>

<template>
  <form ref="root" class="register-form" novalidate @submit.prevent="submit" @focusin="emit('focus-change', true)" @focusout="focusOut">
    <fieldset :disabled="loading">
      <div class="auth-field">
        <label for="register-username">用户名</label>
        <input id="register-username" v-model="username" autocomplete="username" name="username" :disabled="loading" :aria-invalid="Boolean(usernameError || serverError)" :aria-describedby="describedBy(usernameError, 'register-username-error')" @input="usernameError = ''">
        <p v-if="usernameError" id="register-username-error" class="field-error" role="alert">{{ usernameError }}</p>
      </div>
      <div class="auth-field">
        <label for="register-password">密码</label>
        <div class="password-control">
          <input id="register-password" v-model="password" :type="passwordVisible ? 'text' : 'password'" autocomplete="new-password" name="password" :disabled="loading" :aria-invalid="Boolean(passwordError || serverError)" :aria-describedby="describedBy(passwordError, 'register-password-error')" @input="passwordError = ''">
          <ElTooltip :content="passwordVisible ? '隐藏密码' : '显示密码'" placement="top">
            <button type="button" class="password-toggle" data-test="password-toggle" :disabled="loading" :aria-label="passwordVisible ? '隐藏密码' : '显示密码'" @click="passwordVisible = !passwordVisible"><Hide v-if="passwordVisible" /><View v-else /></button>
          </ElTooltip>
        </div>
        <p v-if="passwordError" id="register-password-error" class="field-error" role="alert">{{ passwordError }}</p>
      </div>
      <div class="auth-field major-field">
        <label for="register-major">专业</label>
        <input id="register-major" v-model="major" role="combobox" autocomplete="off" :disabled="loading" aria-autocomplete="list" :aria-expanded="open" aria-controls="register-major-listbox" :aria-activedescendant="activeId" :aria-invalid="Boolean(majorError || serverError)" :aria-describedby="describedBy(majorError, 'register-major-error')" @focus="open = true" @input="updateMajor" @keydown="keydown">
        <ul v-show="open && filteredMajors.length" id="register-major-listbox" class="major-options" role="listbox">
          <li v-for="(item, index) in filteredMajors" :id="`register-major-option-${index}`" :key="item" role="option" :aria-selected="index === activeIndex" :class="{ active: index === activeIndex }" @mousedown.prevent="choose(item)">{{ item }}</li>
        </ul>
        <p v-if="majorError" id="register-major-error" class="field-error" role="alert">{{ majorError }}</p>
      </div>
      <fieldset class="learning-style" :disabled="loading">
        <legend>学习风格 <span>可选</span></legend>
        <div class="style-options">
          <label v-for="item in styles" :key="item.value"><input v-model="learningStyle" type="radio" name="learning-style" :value="item.value" :disabled="loading"><span>{{ item.label }}</span></label>
        </div>
      </fieldset>
      <p v-if="serverError" id="register-server-error" class="server-error" role="alert">{{ serverError }}</p>
      <button class="login-submit" type="submit" :disabled="loading">{{ loading ? '正在创建…' : '创建账户' }}</button>
    </fieldset>
  </form>
</template>
