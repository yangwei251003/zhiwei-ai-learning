import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { postChatStream } from '@/utils/sse'
import { getConversation, listConversations } from '@/api/chat'
import { useUserStore } from './user'

export const useChatStore = defineStore('chat', () => {
  const messages = ref([])
  const traces = ref([])
  const resources = ref([])
  const profileUpdates = ref([])
  const conversationId = ref(null)
  const streaming = ref(false)
  const error = ref('')
  const history = ref([])
  const historyLoading = ref(false)
  const historyError = ref('')
  let controller = null

  const hasMessages = computed(() => messages.value.length > 0)

  async function loadHistory() {
    historyLoading.value = true
    historyError.value = ''
    try {
      history.value = await listConversations()
    } catch (reason) {
      historyError.value = reason.message
    } finally {
      historyLoading.value = false
    }
  }

  async function selectConversation(id) {
    stop()
    historyLoading.value = true
    historyError.value = ''
    try {
      const detail = await getConversation(id)
      conversationId.value = detail.id
      messages.value = detail.messages.map((message) => ({ ...message, status: 'done' }))
      traces.value = []
      resources.value = []
      profileUpdates.value = []
      error.value = ''
    } catch (reason) {
      historyError.value = reason.message
    } finally {
      historyLoading.value = false
    }
  }

  function handleEvent(event, assistant) {
    if (event.type === 'thinking') traces.value.push(event)
    if (event.type === 'token') assistant.content += event.content || ''
    if (event.type === 'resource') resources.value.push(event.payload || event)
    if (event.type === 'profile_update') profileUpdates.value.push(event.payload || event)
    if (event.type === 'error') {
      error.value = event.message || '生成失败'
      assistant.status = 'error'
    }
    if (event.type === 'done') {
      conversationId.value = event.conversation_id || conversationId.value
      if (assistant.status !== 'error') assistant.status = 'done'
    }
  }

  async function sendMessage(content) {
    const message = content.trim()
    if (!message || streaming.value) return
    const userStore = useUserStore()
    const userMessage = { id: crypto.randomUUID(), role: 'user', content: message }
    const assistant = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '',
      status: 'streaming',
    }
    messages.value.push(userMessage, assistant)
    traces.value = []
    error.value = ''
    streaming.value = true
    controller = new AbortController()

    try {
      await postChatStream({
        message,
        conversationId: conversationId.value,
        token: userStore.token,
        signal: controller.signal,
        onEvent: (event) => handleEvent(event, assistant),
      })
      if (assistant.status === 'streaming') {
        assistant.status = 'error'
        error.value = '流式响应在完成前中断'
      }
    } catch (reason) {
      if (reason.name === 'AbortError') {
        assistant.status = 'stopped'
      } else {
        assistant.status = 'error'
        error.value = reason.message
      }
    } finally {
      streaming.value = false
      controller = null
      if (conversationId.value) await loadHistory()
    }
  }

  function stop() {
    controller?.abort()
    streaming.value = false
  }

  function newConversation() {
    stop()
    messages.value = []
    traces.value = []
    resources.value = []
    profileUpdates.value = []
    conversationId.value = null
    error.value = ''
  }

  return {
    messages,
    traces,
    resources,
    profileUpdates,
    conversationId,
    streaming,
    error,
    history,
    historyLoading,
    historyError,
    hasMessages,
    sendMessage,
    loadHistory,
    selectConversation,
    stop,
    newConversation,
  }
})
