<script setup>
import { PhMoon as Moon, PhSun as Sun } from '@phosphor-icons/vue'
import { onMounted } from 'vue'
import { useAppStore } from '@/stores/app'

defineProps({ mode: { type: String, required: true } })
const appStore = useAppStore()
onMounted(() => appStore.initializeTheme())
</script>

<template>
  <main class="auth-layout">
    <section class="auth-story" aria-label="产品介绍">
      <div class="auth-brand"><img src="/assets/mascot-logo.png" width="48" height="48" alt="" /><strong>小智析析</strong></div>
      <div class="auth-copy">
        <p>有画像，有证据，有进度</p>
        <h2>{{ mode === 'login' ? '把每一次提问，变成下一步学习行动。' : '从你的目标出发，建立真正属于你的学习路径。' }}</h2>
        <ul>
          <li>六维画像持续更新</li><li>多智能体协同可观察</li><li>资源与路径完整沉淀</li>
        </ul>
      </div>
      <img class="auth-mascot" :src="mode === 'login' ? '/assets/mascot-thinking.png' : '/assets/mascot-chat.png'" width="300" height="300" alt="小智析析学习助手" />
    </section>
    <section class="auth-form-pane">
      <button class="icon-button auth-theme" type="button" :aria-label="appStore.theme === 'dark' ? '切换到浅色模式' : '切换到深色模式'" @click="appStore.toggleTheme">
        <Sun v-if="appStore.theme === 'dark'" :size="20" /><Moon v-else :size="20" />
      </button>
      <div class="auth-form-wrap"><slot /></div>
    </section>
  </main>
</template>

<style scoped>
.auth-layout { display: grid; min-height: 100dvh; grid-template-columns: minmax(0, 1.08fr) minmax(440px, .92fr); background: var(--color-canvas); }
.auth-story { position: relative; overflow: hidden; min-height: 100dvh; padding: clamp(28px, 5vw, 70px); background: linear-gradient(145deg, rgb(10 19 49 / .92), rgb(38 44 108 / .84)), url('/assets/bg-login.jpg') center/cover; color: #fff; }
.auth-brand { display: flex; align-items: center; gap: 12px; font-size: 20px; }
.auth-brand img { object-fit: contain; }
.auth-copy { position: relative; z-index: 2; max-width: 640px; margin-top: clamp(72px, 14vh, 150px); }
.auth-copy > p { margin-bottom: 16px; color: #dce3ff; font-weight: 700; }
.auth-copy h2 { max-width: 15ch; margin-bottom: 28px; font-size: clamp(36px, 5vw, 66px); line-height: 1.08; letter-spacing: -.035em; }
.auth-copy ul { display: flex; flex-wrap: wrap; gap: 10px 26px; padding: 0; list-style: none; color: #e6e9f7; }
.auth-copy li::before { margin-right: 8px; color: #6ee7b7; content: '●'; font-size: 9px; }
.auth-mascot { position: absolute; right: clamp(-40px, 2vw, 36px); bottom: -18px; object-fit: contain; filter: drop-shadow(0 8px 8px rgb(3 8 28 / .28)); animation: float 5s ease-in-out infinite; }
.auth-form-pane { position: relative; display: grid; min-height: 100dvh; place-items: center; padding: 72px clamp(24px, 7vw, 100px); background: color-mix(in srgb, var(--color-surface) 96%, transparent); }
.auth-theme { position: absolute; top: 24px; right: 24px; }
.auth-form-wrap { width: min(100%, 480px); animation: fadeInUp 420ms var(--ease-out) both; }
@media (max-width: 900px) { .auth-layout { grid-template-columns: 1fr; } .auth-story { display: none; } .auth-form-pane { padding: 70px 20px 32px; } }
@media (prefers-reduced-motion: reduce) { .auth-mascot, .auth-form-wrap { animation: none; } }
</style>
