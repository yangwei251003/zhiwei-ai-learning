<script setup>
import { PhDatabase as Database, PhFloppyDisk as FloppyDisk, PhGear as Gear, PhTrash as Trash, PhUploadSimple as UploadSimple, PhUsers as Users } from '@phosphor-icons/vue'
import { onMounted, reactive, ref } from 'vue'

import PageHeader from '@/components/PageHeader.vue'
import StatePanel from '@/components/StatePanel.vue'
import { deleteKnowledge, getSettings, listKnowledge, listUsers, updateSettings, uploadKnowledge } from '@/api/system'
import { formatDate } from '@/utils/format'

const tabs = [
  { value: 'knowledge', label: '知识库', icon: Database },
  { value: 'users', label: '用户管理', icon: Users },
  { value: 'settings', label: '系统配置', icon: Gear },
]
const activeTab = ref('knowledge')
const documents = ref([])
const users = ref([])
const settings = reactive({})
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const success = ref('')
const fileInput = ref(null)

async function load() {
  loading.value = true; error.value = ''; success.value = ''
  try {
    const [documentData, userData, settingData] = await Promise.all([listKnowledge(), listUsers(), getSettings()])
    documents.value = documentData; users.value = userData; Object.assign(settings, settingData)
  } catch (reason) { error.value = reason.message }
  finally { loading.value = false }
}

async function upload(event) {
  const file = event.target.files?.[0]
  if (!file) return
  saving.value = true; error.value = ''; success.value = ''
  try { await uploadKnowledge(file); documents.value = await listKnowledge(); success.value = `${file.name} 已完成入库` }
  catch (reason) { error.value = reason.message }
  finally { saving.value = false; event.target.value = '' }
}

async function removeDocument(document) {
  saving.value = true; error.value = ''; success.value = ''
  try { await deleteKnowledge(document.id); documents.value = documents.value.filter((item) => item.id !== document.id); success.value = '知识文档已删除' }
  catch (reason) { error.value = reason.message }
  finally { saving.value = false }
}

async function saveSettings() {
  saving.value = true; error.value = ''; success.value = ''
  const payload = {}
  for (const key of ['model_level', 'temperature', 'agent.profile_agent', 'agent.resource_agent', 'agent.path_agent', 'agent.tutor_agent']) {
    if (settings[key] !== undefined && settings[key] !== '') payload[key] = String(settings[key])
  }
  try { Object.assign(settings, await updateSettings(payload)); success.value = '系统配置已保存' }
  catch (reason) { error.value = reason.message }
  finally { saving.value = false }
}

function formatBytes(value) {
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}
onMounted(load)
</script>

<template>
  <div class="admin-page">
    <PageHeader title="管理后台" description="管理真实知识文档、用户与公开系统配置，不显示密钥和私有环境变量。">
      <template #actions><button class="secondary-button" type="button" :disabled="loading" @click="load">刷新数据</button></template>
    </PageHeader>

    <nav class="admin-tabs" aria-label="后台模块"><button v-for="tab in tabs" :key="tab.value" type="button" :class="{ active: activeTab === tab.value }" @click="activeTab = tab.value"><component :is="tab.icon" :size="19" />{{ tab.label }}</button></nav>
    <div v-if="error" class="inline-error admin-message" role="alert">{{ error }}</div>
    <div v-if="success" class="success-message" role="status">{{ success }}</div>
    <StatePanel v-if="loading" state="loading" />

    <section v-else-if="activeTab === 'knowledge'" class="admin-section" aria-labelledby="knowledge-title">
      <div class="section-title"><div><h2 id="knowledge-title">知识库文档</h2><p>支持 PDF、Word、TXT 与 Markdown。文件会切片并写入 FAISS 检索库。</p></div><input ref="fileInput" class="sr-only" type="file" accept=".pdf,.docx,.txt,.md" @change="upload" /><button class="primary-button" type="button" :disabled="saving" @click="fileInput.click()"><UploadSimple :size="18" />{{ saving ? '正在处理' : '上传文档' }}</button></div>
      <StatePanel v-if="!documents.length" state="empty" title="知识库还是空的" message="上传课程资料后，所有 LLM 回答会先检索这些证据。" action-label="选择文档" @action="fileInput.click()" />
      <div v-else class="table-wrap"><table><thead><tr><th>文件</th><th>状态</th><th>切片</th><th>大小</th><th>创建时间</th><th><span class="sr-only">操作</span></th></tr></thead><tbody><tr v-for="document in documents" :key="document.id"><td><strong>{{ document.filename }}</strong><small>{{ document.content_type }}</small></td><td><span :class="['status-text', document.status]">{{ document.status }}</span><small v-if="document.error_message">{{ document.error_message }}</small></td><td>{{ document.chunk_count }}</td><td>{{ formatBytes(document.size_bytes) }}</td><td>{{ formatDate(document.created_at) }}</td><td><button class="table-action danger" type="button" :disabled="saving" :aria-label="`删除 ${document.filename}`" @click="removeDocument(document)"><Trash :size="18" /></button></td></tr></tbody></table></div>
    </section>

    <section v-else-if="activeTab === 'users'" class="admin-section" aria-labelledby="users-title">
      <div class="section-title"><div><h2 id="users-title">用户管理</h2><p>只读展示账户状态与连续学习天数，避免在前端制造未授权写操作。</p></div><span class="record-count">{{ users.length }} 位用户</span></div>
      <StatePanel v-if="!users.length" state="empty" title="还没有注册用户" message="用户完成真实注册后会出现在这里。" />
      <div v-else class="table-wrap"><table><thead><tr><th>用户</th><th>邮箱</th><th>角色</th><th>账户状态</th><th>连续学习</th></tr></thead><tbody><tr v-for="user in users" :key="user.id"><td><strong>{{ user.username }}</strong><small>ID {{ user.id }}</small></td><td>{{ user.email }}</td><td>{{ user.is_admin ? '管理员' : '学习者' }}</td><td><span :class="['status-text', user.is_active ? 'ready' : 'disabled']">{{ user.is_active ? '正常' : '已停用' }}</span></td><td>{{ user.learning_streak }} 天</td></tr></tbody></table></div>
    </section>

    <section v-else class="admin-section settings-section" aria-labelledby="settings-title">
      <div class="section-title"><div><h2 id="settings-title">系统配置</h2><p>仅展示后端白名单字段。真实 Spark 凭据永远不会在页面中读取或显示。</p></div><button class="primary-button" type="button" :disabled="saving" @click="saveSettings"><FloppyDisk :size="18" />{{ saving ? '正在保存' : '保存配置' }}</button></div>
      <form class="settings-form" @submit.prevent="saveSettings">
        <fieldset><legend>模型策略</legend><div class="settings-grid"><div class="field"><label for="model-level">默认模型等级</label><select id="model-level" v-model="settings.model_level"><option value="" disabled>后端尚未设置</option><option value="high">高质量</option><option value="medium">平衡</option><option value="low">低成本</option></select></div><div class="field"><label for="temperature">Temperature</label><input id="temperature" v-model="settings.temperature" type="number" min="0" max="2" step="0.1" placeholder="0 到 2" /></div></div></fieldset>
        <fieldset><legend>Agent 开关</legend><div class="agent-switches"><label v-for="item in [{key:'agent.profile_agent',label:'学生画像'},{key:'agent.resource_agent',label:'资源生成'},{key:'agent.path_agent',label:'路径规划'},{key:'agent.tutor_agent',label:'智能辅导'}]" :key="item.key"><span><strong>{{ item.label }}</strong><small>{{ settings[item.key] === 'true' ? '已启用' : '已停用' }}</small></span><input type="checkbox" :checked="settings[item.key] === 'true'" @change="settings[item.key] = $event.target.checked ? 'true' : 'false'" /></label></div></fieldset>
      </form>
    </section>
  </div>
</template>

<style scoped>
.admin-tabs { display: flex; gap: 5px; margin-bottom: 24px; border-bottom: 1px solid var(--color-border); }.admin-tabs button { display: flex; align-items: center; gap: 7px; min-height: 46px; padding: 9px 15px; border: 0; border-bottom: 2px solid transparent; background: transparent; color: var(--color-ink-secondary); cursor: pointer; }.admin-tabs button.active { border-bottom-color: var(--color-brand-action); color: var(--color-brand-action); font-weight: 800; }.admin-message, .success-message { margin-bottom: 18px; }.success-message { padding: 12px 14px; border-radius: var(--radius-control); background: color-mix(in srgb, var(--color-success) 11%, var(--color-surface)); color: var(--color-ink); }
.admin-section { display: grid; gap: 20px; }.section-title { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; }.section-title h2 { margin-bottom: 5px; font-size: 23px; }.section-title p { max-width: 70ch; margin: 0; color: var(--color-ink-secondary); }.record-count { padding: 6px 10px; border-radius: 999px; background: var(--color-surface-muted); color: var(--color-ink-secondary); font-size: 13px; }
.table-wrap { overflow-x: auto; border-top: 1px solid var(--color-border); }.table-wrap table { width: 100%; min-width: 760px; border-collapse: collapse; }.table-wrap th, .table-wrap td { padding: 14px 12px; border-bottom: 1px solid var(--color-border); text-align: left; vertical-align: middle; }.table-wrap th { color: var(--color-ink-secondary); font-size: 12px; font-weight: 800; }.table-wrap td { font-size: 14px; }.table-wrap td strong, .table-wrap td small { display: block; }.table-wrap td small { color: var(--color-ink-secondary); font-size: 11px; }.status-text { font-size: 12px; font-weight: 800; }.status-text.ready, .status-text.completed { color: var(--color-success); }.status-text.processing { color: var(--color-brand-action); }.status-text.failed, .status-text.disabled { color: var(--color-error); }.table-action { display: inline-grid; width: 36px; height: 36px; padding: 0; place-items: center; border: 0; border-radius: 8px; background: transparent; cursor: pointer; }.table-action:hover { background: var(--color-surface-muted); }.table-action.danger { color: var(--color-error); }
.settings-form { display: grid; gap: 28px; max-width: 980px; }.settings-form fieldset { margin: 0; padding: 24px; border: 1px solid var(--color-border); border-radius: var(--radius-card); }.settings-form legend { padding: 0 7px; font-weight: 800; }.settings-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }.agent-switches { display: grid; grid-template-columns: 1fr 1fr; gap: 1px; background: var(--color-border); }.agent-switches label { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 16px; background: var(--color-surface); cursor: pointer; }.agent-switches label span { display: grid; }.agent-switches small { color: var(--color-ink-secondary); }.agent-switches input { width: 20px; height: 20px; accent-color: var(--color-brand-action); }
@media (max-width: 700px) { .section-title { align-items: stretch; flex-direction: column; }.section-title > button { width: 100%; }.settings-grid, .agent-switches { grid-template-columns: 1fr; }.admin-tabs { overflow-x: auto; }.admin-tabs button { white-space: nowrap; } }
</style>
