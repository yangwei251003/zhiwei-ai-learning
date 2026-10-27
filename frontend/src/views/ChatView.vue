<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '../components/product/AppShell.vue'
import AiCreating from '../components/product/AiCreating.vue'
import ResourceCard from '../components/product/ResourceCard.vue'
import { useUserStore } from '../stores/user'
import type { LearningResource, Profile } from '../types/product'
import { parseSseBlock } from '../utils/sse'
import http, { resolveApiUrl } from '../utils/http'

interface Message { role: 'user' | 'assistant'; content: string; resources?: LearningResource[]; error?: boolean }
const user = useUserStore(); const router = useRouter(); const input = ref(''); const messages = ref<Message[]>([])
const sending = ref(false); const reconnecting = ref(false); const creating = ref(false); const profile = ref<Profile | null>(null)
const knowledgeConnected = ref(false); const conversationId = ref<number>(); const scrollEl = ref<HTMLElement>()
const canSend = computed(() => input.value.trim().length > 0 && input.value.length <= 5000 && !sending.value)

async function loadSideData() {
  const [p, k] = await Promise.allSettled([http.get<Profile>('/api/profile/current'), http.get('/api/knowledge/list')])
  if (p.status === 'fulfilled') profile.value = p.value.data
  knowledgeConnected.value = k.status === 'fulfilled' && k.value.data.length > 0
}

async function consume(response: Response, assistant: Message) {
  const reader = response.body?.getReader(); if (!reader) throw new Error('流式连接不可用')
  const decoder = new TextDecoder(); let buffer = ''
  while (true) {
    const { done, value } = await reader.read(); if (done) break
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n')
    const blocks = buffer.split('\n\n'); buffer = blocks.pop() || ''
    for (const block of blocks) {
      const event = parseSseBlock(block); if (!event) continue
      if (event.type === 'token') assistant.content += String(event.payload.content || '')
      if (event.type === 'resource') { assistant.resources ||= []; assistant.resources.push(event.payload as unknown as LearningResource); creating.value = false }
      if (event.type === 'profile_update') profile.value = { ...(profile.value || {} as Profile), ...(event.payload as Partial<Profile>) }
      if (event.type === 'thinking') creating.value = /生成|文档|资源/.test(messages.value.at(-2)?.content || '')
      if (event.type === 'error') throw new Error(String(event.payload.detail || '讯飞服务暂时不可用'))
      if (event.type === 'done' && event.payload.conversation_id) conversationId.value = Number(event.payload.conversation_id)
      await nextTick(); scrollEl.value?.scrollTo({ top: scrollEl.value.scrollHeight, behavior: 'smooth' })
    }
  }
}

async function streamMessage(text: string, assistant: Message) {
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const original = assistant.content; const originalResources = assistant.resources ? [...assistant.resources] : undefined
    try {
      reconnecting.value = attempt > 0
      const response = await fetch(resolveApiUrl('/api/chat/stream'), { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${user.token}` }, body: JSON.stringify({ message: text, course: profile.value?.major || 'Python', conversation_id: conversationId.value }) })
      if (response.status === 401) { user.logout(); await router.replace('/login'); return }
      if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail || `服务请求失败（${response.status}）`) }
      await consume(response, assistant); reconnecting.value = false; return
    } catch (error) {
      assistant.content = original; assistant.resources = originalResources
      if (attempt === 2 || (error instanceof Error && /讯飞|服务请求失败/.test(error.message))) throw error
      await new Promise((resolve) => window.setTimeout(resolve, 500 * (attempt + 1)))
    }
  }
}

async function send() {
  const text = input.value.trim(); if (!text || !canSend.value) return
  messages.value.push({ role: 'user', content: text }); const assistant: Message = { role: 'assistant', content: '' }; messages.value.push(assistant)
  input.value = ''; sending.value = true
  try { await streamMessage(text, assistant); if (!assistant.content && !assistant.resources?.length) assistant.content = '任务已完成，可以前往对应页面查看结果。'; await loadSideData() }
  catch (error) { assistant.error = true; assistant.content = error instanceof Error ? error.message : '连接失败，请稍后重试' }
  finally { sending.value = false; reconnecting.value = false; creating.value = false }
}

onMounted(loadSideData)
</script>

<template><AppShell><div class="chat-layout"><aside class="conversation-rail"><span class="eyebrow">当前会话</span><button class="new-chat" @click="messages = []; conversationId = undefined">＋ 新对话</button><div class="conversation-item active">Python 学习计划<small>刚刚</small></div><div class="kb-state"><span :class="['live-dot', { muted: !knowledgeConnected }]" />{{ knowledgeConnected ? '知识库已接入' : '知识库未接入' }}<small>{{ knowledgeConnected ? '回答会引用课程资料' : '将使用通用模型回答' }}</small></div></aside><section class="chat-center"><header><div><span class="eyebrow">多智能体协作会话</span><h1>和小智析析一起拆解问题</h1></div><span v-if="reconnecting" class="reconnect-badge">连接中断，正在自动重连…</span></header><div ref="scrollEl" class="message-list"><div v-if="!messages.length" class="chat-welcome"><img src="/assets/mascot-chat.png" alt="小智析析" /><h2>从一句真实目标开始</h2><p>例如：“我是电气工程专业的学生，想学 Python 基础”</p></div><article v-for="(message, index) in messages" :key="index" :class="['message', message.role, { error: message.error }]"><span class="avatar">{{ message.role === 'user' ? '我' : '析' }}</span><div><p>{{ message.content }}<span v-if="message.role === 'assistant' && sending && index === messages.length - 1" class="cursor" /></p><div v-if="message.resources?.length" class="inline-resources"><ResourceCard v-for="resource in message.resources" :key="resource.id" :resource="resource" @select="router.push(`/resources?id=${$event}`)" /></div></div></article><AiCreating v-if="creating" label="AI 正在创造学习资源" /></div><form class="composer" @submit.prevent="send"><textarea v-model="input" maxlength="5000" rows="2" placeholder="描述你的学习目标或问题…" @keydown.enter.exact.prevent="send" /><div><span :class="{ danger: input.length > 4900 }">{{ input.length }}/5000</span><button class="send-button" :disabled="!canSend">{{ sending ? '思考中' : '发送 ↑' }}</button></div></form></section><aside class="profile-panel"><span class="eyebrow">实时学习画像</span><img src="/assets/mascot-thinking.png" alt="分析中的小智析析" loading="lazy" /><h2>{{ profile?.major || '等待认识你' }}</h2><dl><div><dt>学习风格</dt><dd>{{ profile?.cognitive_style || '待识别' }}</dd></div><div><dt>学习目标</dt><dd>{{ profile?.learning_goal || '通过对话自动提取' }}</dd></div><div><dt>兴趣方向</dt><dd>{{ profile?.interests || '持续探索中' }}</dd></div></dl><div class="profile-energy"><span>画像完整度</span><div><i :style="{ width: profile?.major ? '72%' : '28%' }" /></div></div></aside></div></AppShell></template>
