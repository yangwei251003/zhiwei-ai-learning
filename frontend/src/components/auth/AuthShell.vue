<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Moon, Sunny } from '@element-plus/icons-vue'
import { ElTooltip } from 'element-plus'
import BrandConstellation from './BrandConstellation.vue'

withDefaults(defineProps<{ celebrating?: boolean; focused?: boolean }>(), {
  celebrating: false,
  focused: true,
})

const THEME_KEY = 'zhiwei.theme'
const isDark = ref(false)

const themeLabel = computed(() => isDark.value ? '切换到浅色主题' : '切换到深色主题')

function applyTheme(dark: boolean) {
  isDark.value = dark
  document.documentElement.classList.toggle('dark', dark)
}

function toggleTheme() {
  applyTheme(!isDark.value)
  localStorage.setItem(THEME_KEY, isDark.value ? 'dark' : 'light')
}

onMounted(() => {
  const savedTheme = localStorage.getItem(THEME_KEY)
  const prefersDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
  applyTheme(savedTheme ? savedTheme === 'dark' : prefersDark)
})
</script>

<template>
  <main class="auth-shell">
    <section class="auth-content" aria-label="账户访问">
      <header class="auth-header">
        <a class="auth-brand" href="/" aria-label="知微智学首页">
          <img src="/assets/mascot-logo.png" alt="知微智学小智析析标识">
          <strong>知微智学</strong>
        </a>
        <ElTooltip :content="themeLabel" placement="bottom">
          <button
            class="theme-toggle"
            type="button"
            data-test="theme-toggle"
            :aria-label="themeLabel"
            @click="toggleTheme"
          >
            <Sunny v-if="isDark" />
            <Moon v-else />
          </button>
        </ElTooltip>
      </header>

      <div class="auth-form-region">
        <slot />
      </div>
      <footer class="auth-footer"><slot name="footer" /></footer>
    </section>

    <aside class="auth-brand-stage" aria-label="知微智学品牌故事">
      <div class="auth-stage-copy">
        <h1>学习，从被理解开始</h1>
        <ul class="auth-facts" aria-label="产品特点">
          <li><strong>多智能体</strong><span>协作理解</span></li>
          <li><strong>个性化</strong><span>动态适配</span></li>
          <li><strong>即时生成</strong><span>所学即得</span></li>
        </ul>
      </div>
      <BrandConstellation :focused="focused" :celebrating="celebrating" />
    </aside>
  </main>
</template>
