<script setup>
import {
  PhArrowDown as ArrowDown,
  PhBookOpenText as BookOpenText,
  PhCaretDoubleDown as CaretDoubleDown,
  PhCaretDoubleUp as CaretDoubleUp,
  PhPaperPlaneRight as PaperPlaneRight,
  PhPlus as Plus,
  PhStop as Stop,
  PhUserFocus as UserFocus,
} from '@phosphor-icons/vue'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import MarkdownContent from '@/components/MarkdownContent.vue'
import { useChatStore } from '@/stores/chat'

const chatStore = useChatStore()
const draft = ref('')
const messageList = ref(null)
const profileDimensions = ['知识基础', '认知风格', '易错点', '学习目标', '专业方向', '兴趣偏好']
const latestProfile = computed(() => Object.fromEntries(chatStore.profileUpdates.map((item) => [item.dimension, item.value])))

// === Smart auto-scroll ===
// Only scroll to bottom when the user is already near the bottom (within 80px).
// When the user scrolls up to read past content, stop auto-scrolling and show a "scroll to bottom" button.
const stickToBottom = ref(true)
const showScrollButton = ref(false)
const expandedMessages = ref(new Set())
const SCROLL_THRESHOLD = 80

function onScroll() {
  if (!messageList.value) return
  const { scrollTop, scrollHeight, clientHeight } = messageList.value
  const distanceFromBottom = scrollHeight - scrollTop - clientHeight
  const nearBottom = distanceFromBottom <= SCROLL_THRESHOLD
  stickToBottom.value = nearBottom
  showScrollButton.value = !nearBottom && scrollHeight > clientHeight + 200
}

async function scrollToBottom(smooth = true) {
  await nextTick()
  if (!messageList.value) return
  messageList.value.scrollTo({ top: messageList.value.scrollHeight, behavior: smooth ? 'smooth' : 'auto' })
  stickToBottom.value = true
  showScrollButton.value = false
}

watch(() => chatStore.messages.map((item) => item.content).join(''), async () => {
  if (stickToBottom.value) {
    await scrollToBottom()
  }
})

function isMessageExpanded(id) {
  return expandedMessages.value.has(id)
}

function toggleMessageExpansion(id) {
  if (expandedMessages.value.has(id)) {
    expandedMessages.value.delete(id)
  } else {
    expandedMessages.value.add(id)
  }
  // force reactivity
  expandedMessages.value = new Set(expandedMessages.value)
}

function shouldCollapse(message) {
  // Collapse if assistant content is over 1200 chars and not already expanded
  if (message.role !== 'assistant') return false
  if (message.status === 'streaming') return false
  return (message.content?.length || 0) > 1200 && !isMessageExpanded(message.id)
}

function truncatedContent(message) {
  if (!message.content) return ''
  return message.content.slice(0, 1200) + '…'
}

async function submit() {
  const content = draft.value
  if (!content.trim() || chatStore.streaming) return
  draft.value = ''
  stickToBottom.value = true
  await chatStore.sendMessage(content)
  await scrollToBottom(false)
}

function keydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); submit() }
}

onBeforeUnmount(() => chatStore.stop())
onMounted(async () => {
  await chatStore.loadHistory()
  await nextTick()
  if (messageList.value) messageList.value.addEventListener('scroll', onScroll, { passive: true })
})
</script>

<template>
  <div class="chat-page">
    <header class="chat-titlebar">
      <div>
        <h1>学习对话</h1>
        <p>每轮回答都会先检索知识库，并显示参与协作的 Agent。</p>
      </div>
      <button class="secondary-button" type="button" :disabled="chatStore.streaming" @click="chatStore.newConversation">
        <Plus :size="18" />新对话
      </button>
    </header>

    <div class="chat-workspace">
      <section class="history-panel" role="region" aria-label="对话历史">
        <h2>对话历史</h2>
        <div v-if="chatStore.historyLoading && !chatStore.history.length" class="history-loading" aria-label="正在加载对话历史">
          <span class="skeleton-line" /><span class="skeleton-line short" />
        </div>
        <div v-else-if="chatStore.historyError && !chatStore.history.length" class="history-error" role="alert">
          <span>{{ chatStore.historyError }}</span>
          <button type="button" @click="chatStore.loadHistory">重试</button>
        </div>
        <div v-else-if="chatStore.history.length" class="history-list">
          <button
            v-for="conversation in chatStore.history"
            :key="conversation.id"
            :class="['history-item', { 'is-active': chatStore.conversationId === conversation.id }]"
            type="button"
            :disabled="chatStore.historyLoading"
            :aria-current="chatStore.conversationId === conversation.id ? 'true' : undefined"
            @click="chatStore.selectConversation(conversation.id)"
          >
            <span>{{ conversation.title }}</span>
            <small>{{ conversation.message_count }} 条消息</small>
          </button>
        </div>
        <div v-else class="compact-empty">
          <img src="/assets/mascot-empty.png" width="92" height="92" alt="" />
          <strong>还没有对话</strong>
          <span>从中间的问题框开始。</span>
        </div>
      </section>

      <section class="conversation-panel" role="region" aria-label="当前对话">
        <div ref="messageList" class="message-list" aria-live="polite">
          <div v-if="!chatStore.hasMessages" class="chat-empty">
            <img src="/assets/mascot-chat.png" width="150" height="150" alt="小智析析微笑着等待问题" />
            <h2>把你真正卡住的地方告诉我</h2>
            <p>可以说明课程、当前基础、目标和希望采用的讲解方式。</p>
            <div class="prompt-starters">
              <button type="button" @click="draft = '我总是分不清进程和线程，请结合生活例子解释'">区分进程与线程</button>
              <button type="button" @click="draft = '帮我规划一周的概率论复习路径，每天 40 分钟'">规划概率论复习</button>
            </div>
          </div>

          <article
            v-for="message in chatStore.messages"
            :key="message.id"
            :class="['message', `message-${message.role}`]"
          >
            <img v-if="message.role === 'assistant'" src="/assets/mascot-chat.png" width="38" height="38" alt="" class="message-avatar" />
            <div class="message-body">
              <span class="message-role">{{ message.role === 'user' ? '你' : '小智析析' }}</span>
              <div v-if="message.role === 'assistant'" class="message-content-wrap">
                <MarkdownContent
                  v-if="!shouldCollapse(message)"
                  :source="message.content || (message.status === 'streaming' ? '正在组织回答…' : '')"
                />
                <MarkdownContent v-else :source="truncatedContent(message)" />
                <button
                  v-if="(message.content?.length || 0) > 1200 && message.status !== 'streaming'"
                  class="message-toggle"
                  type="button"
                  @click="toggleMessageExpansion(message.id)"
                >
                  <CaretDoubleDown v-if="!isMessageExpanded(message.id)" :size="14" />
                  <CaretDoubleUp v-else :size="14" />
                  {{ isMessageExpanded(message.id) ? '收起回答' : '展开完整回答' }}
                </button>
              </div>
              <p v-else class="message-text">{{ message.content }}</p>
              <span v-if="message.status === 'streaming'" class="typing-cursor" aria-label="正在生成" />
              <span v-if="message.status === 'error'" class="message-failed">本轮生成未完成</span>
              <span v-if="message.status === 'stopped'" class="message-stopped">已停止生成</span>
            </div>
          </article>

          <div v-if="chatStore.traces.length" class="agent-trace" aria-label="Agent 协作轨迹">
            <strong>协作轨迹</strong>
            <ol>
              <li v-for="trace in chatStore.traces" :key="`${trace.sequence}-${trace.agent}`">
                <span class="trace-dot" />{{ trace.content }}
              </li>
            </ol>
          </div>
          <div v-if="chatStore.error" class="inline-error" role="alert">
            <strong>真实服务错误</strong>
            <span>{{ chatStore.error }}</span>
          </div>
          <div v-if="chatStore.resources.length" class="created-resources">
            <strong>本轮已生成资源</strong>
            <RouterLink v-for="resource in chatStore.resources" :key="resource.id || resource.title" to="/resources">
              <BookOpenText :size="18" />{{ resource.title }}
            </RouterLink>
          </div>
        </div>

        <button
          v-show="showScrollButton"
          class="scroll-to-bottom"
          type="button"
          aria-label="跳到最新消息"
          @click="scrollToBottom(true)"
        >
          <ArrowDown :size="18" weight="bold" />
          <span>最新消息</span>
        </button>

        <form class="composer" @submit.prevent="submit">
          <label class="sr-only" for="chat-draft">给小智析析发消息</label>
          <textarea
            id="chat-draft"
            v-model="draft"
            rows="2"
            maxlength="10000"
            placeholder="描述你的问题、目标或不理解的步骤"
            :disabled="chatStore.streaming"
            @keydown="keydown"
          />
          <button
            v-if="chatStore.streaming"
            class="secondary-button composer-action"
            type="button"
            @click="chatStore.stop"
          >
            <Stop :size="18" weight="fill" />停止
          </button>
          <button
            v-else
            class="primary-button composer-action"
            type="submit"
            :disabled="!draft.trim()"
          >
            <PaperPlaneRight :size="18" weight="fill" />发送
          </button>
        </form>
      </section>

      <section class="profile-panel" role="region" aria-label="六维画像">
        <div class="panel-heading">
          <UserFocus :size="22" weight="duotone" />
          <div>
            <h2>六维画像</h2>
            <p>只展示本轮已确认变化</p>
          </div>
        </div>
        <dl>
          <div v-for="dimension in profileDimensions" :key="dimension">
            <dt>{{ dimension }}</dt>
            <dd :class="{ pending: !latestProfile[dimension] }">
              {{ latestProfile[dimension] || '待对话了解' }}
            </dd>
          </div>
        </dl>
        <div class="evidence-note">
          <strong>画像如何使用</strong>
          <p>画像会影响检索、讲解深度和路径顺序，不作为能力评分。</p>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
/* === Layout ===
   Use a flex column for the page and workspace so heights are computed
   deterministically and the message-list can scroll without bleeding out. */
.chat-page {
  display: flex;
  flex-direction: column;
  /* Subtract the sticky topbar (64px) and the page-stage padding (~48px top + ~48px bottom).
     Use min-height so on small viewports the chat still has room to render. */
  height: calc(100dvh - 64px - clamp(44px, 8vw, 96px));
  min-height: 540px;
}

.chat-titlebar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  flex: 0 0 auto;
  margin-bottom: 16px;
}
.chat-titlebar h1 { margin-bottom: 5px; font-size: 30px; }
.chat-titlebar p { margin: 0; color: var(--color-ink-secondary); font-size: 14px; }

/* chat-workspace: flex column (single row) using flex for the columns.
   Flex gives us reliable height propagation without the quirks of
   nested grid + min-height: 0. */
.chat-workspace {
  display: flex;
  flex: 1 1 auto;
  min-height: 0;        /* allow this flex child to shrink so the inner panel can scroll */
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-card);
  background: var(--color-surface);
}

/* === History panel (left) === */
.history-panel,
.profile-panel {
  flex: 0 0 auto;
  width: 220px;
  overflow-y: auto;
  padding: 20px 16px;
  background: color-mix(in srgb, var(--color-surface-muted) 58%, var(--color-surface));
  scrollbar-width: thin;
}
.history-panel { border-right: 1px solid var(--color-border); }
.profile-panel { border-left: 1px solid var(--color-border); width: 300px; }


.history-panel h2,
.profile-panel h2 { margin-bottom: 14px; font-size: 16px; }
.history-list { display: grid; gap: 5px; }
.history-item {
  display: grid; width: 100%; gap: 2px; padding: 12px;
  border: 0; border-radius: var(--radius-control);
  background: transparent; color: var(--color-ink);
  text-align: left; cursor: pointer;
}
.history-item:hover { background: var(--color-surface); }
.history-item.is-active { background: var(--color-brand-soft); color: var(--color-brand-action); }
.history-item:disabled { cursor: wait; opacity: .65; }
.history-item small { color: var(--color-ink-secondary); }
.history-loading { display: grid; gap: 8px; padding-top: 8px; }
.history-loading .short { width: 72%; }
.history-error { display: grid; gap: 8px; color: var(--color-error); font-size: 13px; }
.history-error button { justify-self: start; padding: 5px 0; border: 0; background: transparent; color: var(--color-brand-action); font-weight: 800; cursor: pointer; }
.compact-empty { display: grid; justify-items: center; padding: 44px 4px; color: var(--color-ink-secondary); text-align: center; }
.compact-empty strong { color: var(--color-ink); }
.compact-empty span { font-size: 13px; }

/* === Conversation panel (center) === */
.conversation-panel {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-width: 0;
  min-height: 0;       /* critical: lets the flex child shrink so the message-list can scroll */
  position: relative;
}

.message-list {
  flex: 1 1 auto;
  min-height: 0;       /* critical: lets this child shrink so overflow-y works */
  overflow-y: auto;
  padding: 26px clamp(18px, 4vw, 54px) 16px;
  scroll-behavior: smooth;
  scrollbar-width: thin;
  scrollbar-color: color-mix(in srgb, var(--color-ink-secondary) 30%, transparent) transparent;
  scroll-padding-bottom: 80px; /* keep some space below the last message */
}
.message-list::-webkit-scrollbar { width: 8px; }
.message-list::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, var(--color-ink-secondary) 30%, transparent);
  border-radius: 4px;
}
.message-list::-webkit-scrollbar-thumb:hover {
  background: color-mix(in srgb, var(--color-ink-secondary) 50%, transparent);
}

/* Empty state */
.chat-empty {
  display: grid;
  min-height: 100%;
  place-items: center;
  align-content: center;
  text-align: center;
}
.chat-empty h2 { margin: 9px 0 5px; font-size: 22px; }
.chat-empty p { max-width: 50ch; color: var(--color-ink-secondary); }
.prompt-starters { display: flex; flex-wrap: wrap; justify-content: center; gap: 9px; margin-top: 12px; }
.prompt-starters button {
  padding: 8px 11px; border: 1px solid var(--color-border);
  border-radius: var(--radius-control); background: var(--color-surface);
  color: var(--color-ink-secondary); cursor: pointer;
}
.prompt-starters button:hover { color: var(--color-ink); background: var(--color-surface-muted); }

/* === Messages === */
.message {
  display: flex;
  gap: 11px;
  max-width: 820px;
  margin: 0 auto 24px;
  width: 100%;
  word-wrap: break-word;
  overflow-wrap: anywhere;
}
.message-user { margin-left: auto; flex-direction: row-reverse; }
.message-user .message-body {
  padding: 13px 16px;
  border-radius: var(--radius-card) var(--radius-card) 3px var(--radius-card);
  background: var(--color-brand-action);
  color: #fff;
  max-width: 78%;
}
.message-user p { margin: 0; white-space: pre-wrap; }

.message-assistant { align-items: flex-start; }
.message-avatar { flex: 0 0 auto; object-fit: contain; margin-top: 2px; }
.message-assistant .message-body {
  min-width: 0;
  flex: 1 1 auto;
  max-width: calc(100% - 50px);
}
.message-role { display: block; margin-bottom: 5px; color: inherit; font-size: 12px; font-weight: 800; }
.message-assistant .message-role { color: var(--color-brand-action); }

.message-content-wrap { position: relative; }
.message-failed, .message-stopped { display: block; margin-top: 8px; font-size: 13px; }
.message-failed { color: var(--color-error); }
.message-stopped { color: var(--color-ink-secondary); }
.typing-cursor {
  display: inline-block; width: 2px; height: 1em; margin-left: 3px;
  background: var(--color-brand-action); vertical-align: text-bottom;
  animation: typingCursor .8s step-end infinite;
}

.message-toggle {
  display: inline-flex; align-items: center; gap: 5px;
  margin-top: 10px; padding: 5px 11px;
  border: 1px solid var(--color-border); border-radius: var(--radius-control);
  background: var(--color-surface-muted); color: var(--color-brand-action);
  font-size: 12px; font-weight: 700; cursor: pointer;
  transition: background var(--duration-fast) ease;
}
.message-toggle:hover { background: var(--color-brand-soft); }

/* Agent trace + errors + resources */
.agent-trace { margin: 0 auto 22px; max-width: 820px; padding: 14px 16px; border-radius: var(--radius-control); background: var(--color-surface-muted); }
.agent-trace strong { font-size: 13px; }
.agent-trace ol { display: grid; gap: 6px; margin: 8px 0 0; padding: 0; list-style: none; }
.agent-trace li { display: flex; align-items: center; gap: 8px; color: var(--color-ink-secondary); font-size: 13px; }
.trace-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--color-brand-action); }
.agent-trace li:last-child .trace-dot { animation: breathe 1.2s ease-in-out infinite; }
.inline-error { display: grid; margin: 0 auto 18px; max-width: 820px; }
.created-resources { display: grid; gap: 7px; margin: 0 auto 18px; max-width: 820px; }
.created-resources > strong { font-size: 13px; }
.created-resources a { display: flex; align-items: center; gap: 8px; color: var(--color-brand-action); font-size: 14px; font-weight: 700; }

/* === Scroll to bottom floating button === */
.scroll-to-bottom {
  position: absolute;
  right: 22px;
  bottom: 90px; /* sits above the composer */
  display: inline-flex; align-items: center; gap: 5px;
  padding: 7px 12px;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: var(--color-surface);
  color: var(--color-brand-action);
  font-size: 12px; font-weight: 700;
  box-shadow: 0 4px 14px color-mix(in srgb, var(--color-ink) 18%, transparent);
  cursor: pointer;
  z-index: 5;
  transition: transform var(--duration-fast) ease, box-shadow var(--duration-fast) ease;
}
.scroll-to-bottom:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px color-mix(in srgb, var(--color-ink) 22%, transparent);
}

/* === Composer === */
.composer {
  flex: 0 0 auto;       /* never shrink — always full size at bottom */
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  padding: 14px 18px;
  border-top: 1px solid var(--color-border);
  background: var(--color-surface);
  position: relative;
  z-index: 2;
}
.composer textarea {
  min-height: 52px; max-height: 150px;
  padding: 12px 13px;
  border: 1px solid var(--color-border); border-radius: var(--radius-control);
  background: var(--color-surface-muted); color: var(--color-ink);
  resize: none;
}
.composer-action { align-self: end; }

/* === Profile panel === */
.panel-heading { display: flex; gap: 9px; align-items: flex-start; margin-bottom: 14px; }
.panel-heading svg { color: var(--color-brand-action); }
.panel-heading h2 { margin: 0; }
.panel-heading p { margin: 0; color: var(--color-ink-secondary); font-size: 12px; }
.profile-panel dl { margin: 0; }
.profile-panel dl > div { padding: 13px 0; border-bottom: 1px solid var(--color-border); }
.profile-panel dt { color: var(--color-ink-secondary); font-size: 12px; }
.profile-panel dd { margin: 3px 0 0; font-size: 14px; font-weight: 700; }
.profile-panel dd.pending { color: var(--color-ink-secondary); font-weight: 500; }
.evidence-note {
  margin-top: 20px; padding: 14px;
  border-radius: var(--radius-control);
  background: color-mix(in srgb, var(--color-success) 10%, var(--color-surface));
}
.evidence-note strong { font-size: 13px; }
.evidence-note p { margin: 4px 0 0; color: var(--color-ink-secondary); font-size: 12px; }

/* === Responsive === */
@media (max-width: 1180px) {
  .history-panel { width: 200px; }
  .profile-panel { display: none; }
}
@media (max-width: 760px) {
  .chat-page { min-height: 460px; }
  .chat-titlebar { align-items: stretch; flex-direction: column; }
  .chat-workspace { flex-direction: column; }
  .history-panel, .profile-panel { width: 100%; border: 0; border-bottom: 1px solid var(--color-border); max-height: 140px; }
  .message-list { padding: 18px 13px 12px; }
  .message { max-width: 100%; }
  .message-user .message-body { max-width: 85%; }
  .composer { padding: 10px; }
  .composer-action { min-width: 48px; padding-inline: 12px; }
  .scroll-to-bottom { right: 14px; bottom: 76px; }
}
@media (prefers-reduced-motion: reduce) {
  .typing-cursor, .agent-trace li:last-child .trace-dot { animation: none; }
  .message-list { scroll-behavior: auto; }
}
</style>
