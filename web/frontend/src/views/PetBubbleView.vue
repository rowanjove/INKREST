<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, nextTick } from 'vue'
import { usePetStore } from '../stores/pet'
import { abortTask } from '../api'
import {
  SHANSHAN_BATCH_PAUSE_HINT,
  SHANSHAN_CHAT_PLACEHOLDER,
  SHANSHAN_CHAT_SCOPE,
  SHANSHAN_SUGGESTED_QUESTIONS,
} from '../constants/shanshanCopy'

const pet = usePetStore()
const avatar = new URL('../assets/pet/shanshan/ui/bubble_avatar.png', import.meta.url).href

const activeTab = ref<'status' | 'chat'>('status')
const inputMessage = ref('')
const chatContainer = ref<HTMLElement | null>(null)
const chatInputRef = ref<HTMLTextAreaElement | null>(null)
const diagnoseCollapsed = ref(JSON.parse(localStorage.getItem('pet_diagnose_collapsed') || 'false'))

function toggleDiagnoseCollapsed() {
  diagnoseCollapsed.value = !diagnoseCollapsed.value
  localStorage.setItem('pet_diagnose_collapsed', JSON.stringify(diagnoseCollapsed.value))
}

const suggestedQuestions = [...SHANSHAN_SUGGESTED_QUESTIONS]

function navigate(route: string) {
  window.electronAPI?.navigateMain?.(route)
}

function handleStatusCardClick() {
  const failed = pet.latestFailedTask
  if (failed?.chapter_id) {
    navigate(`/chapters/${failed.chapter_id}`)
    return
  }
  if (
    pet.novelBatchPaused ||
    failed ||
    pet.context?.running_tasks?.length ||
    (pet.context?.pipeline_pending?.pending_total ?? 0) > 0
  ) {
    navigate('/chapters/maintenance')
  }
}

function openMonitorForBatch() {
  navigate('/chapters/maintenance')
}

function selectTab(tab: 'status' | 'chat') {
  activeTab.value = tab
  if (tab === 'chat') {
    pet.initChatHistory()
    scrollToBottom()
    nextTick(() => chatInputRef.value?.focus())
  }
}

function handleInputKeydown(event: KeyboardEvent) {
  if (event.key !== 'Enter') return
  if (event.shiftKey) return
  event.preventDefault()
  handleSend()
}

async function handleSend() {
  if (!inputMessage.value.trim() || pet.chatLoading) return
  const msg = inputMessage.value
  inputMessage.value = ''
  await pet.sendChatMessage(msg)
  scrollToBottom()
}

function handleSuggestQuestion(q: string) {
  if (pet.chatLoading) return
  inputMessage.value = q
  handleSend()
}

async function handleActionClick(action: any) {
  if (action.type === 'navigate') {
    navigate(action.payload?.route || '/')
  } else {
    await pet.executeFix(action.type, action.payload || {})
    scrollToBottom()
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
    }
  })
}

// 简易 Markdown 渲染，保证极轻量且无外部依赖
function renderMarkdown(text: string) {
  if (!text) return ''
  // 转义基础 HTML 标签防止注入
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  // 渲染粗体 **bold**
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
  // 渲染斜体 *italic*
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>')
  // 渲染行内代码 `code`
  html = html.replace(/`(.*?)`/g, '<code>$1</code>')
  // 渲染换行
  html = html.replace(/\n/g, '<br>')
  // 渲染列表项
  html = html.replace(/(?:^|<br>)\s*-\s+(.*?)(?=$|<br>)/g, (_, p1) => {
    return `<div class="md-list-item"><span class="bullet">•</span> ${p1}</div>`
  })

  return html
}

async function handleAbortRunningTask() {
  const task = pet.context?.running_tasks?.[0]
  if (!task || !task.id) return
  try {
    await abortTask(task.id)
    await pet.refreshContext()
  } catch (e) {
    console.error('Failed to abort task:', e)
  }
}

onMounted(async () => {
  await pet.loadSettings()
  await pet.refreshContext()
  await pet.runDiagnose()
  pet.startPolling()
})

onBeforeUnmount(() => {
  pet.stopPolling()
})
</script>

<template>
  <main class="bubble-shell">
    <!-- 合并的头部与 Tab 行 -->
    <header class="bubble-header-bar">
      <div class="header-left-brand">
        <div class="avatar-mini-wrap">
          <img :src="avatar" alt="" draggable="false" class="avatar-mini" />
          <span class="status-pulse-mini" :class="pet.bubblePulseState" />
        </div>
        <div class="brand-text">
          <strong>山山</strong>
          <span class="brand-sub">小编辑</span>
        </div>
      </div>
      <!-- Tab 切换 -->
      <nav class="bubble-tabs-compact">
        <button
          type="button"
          class="tab-btn-mini"
          :class="{ active: activeTab === 'status' }"
          @click="selectTab('status')"
        >
          状态
        </button>
        <button
          type="button"
          class="tab-btn-mini"
          :class="{ active: activeTab === 'chat' }"
          @click="selectTab('chat')"
        >
          对话
        </button>
      </nav>
    </header>

    <!-- 主体区域：状态与诊断 -->
    <section v-if="activeTab === 'status'" class="tab-content-status">
      <div
        v-if="pet.novelBatchPaused && pet.context?.novel_batch"
        class="batch-pause-banner"
        role="button"
        tabindex="0"
        @click="openMonitorForBatch"
        @keydown.enter="openMonitorForBatch"
      >
        <span class="batch-pause-icon">⏸</span>
        <p class="batch-pause-text">{{ SHANSHAN_BATCH_PAUSE_HINT(pet.context.novel_batch) }}</p>
        <span class="batch-pause-cta">去章节维护续跑 →</span>
      </div>

      <!-- 紧凑型状态卡片 -->
      <div 
        class="status-card-compact" 
        :class="{
          clickable:
            pet.novelBatchPaused ||
            pet.latestFailedTask ||
            pet.context?.running_tasks?.length ||
            (pet.context?.pipeline_pending?.pending_total ?? 0) > 0,
        }"
        @click="handleStatusCardClick"
      >
        <div class="status-title-row">
          <span
            class="status-indicator-dot"
            :class="{
              alert: pet.novelBatchPaused || pet.latestFailedTask || pet.lastError,
              busy: !pet.novelBatchPaused && pet.context?.running_tasks?.length,
            }"
          />
          <span class="status-text-bold">{{ pet.statusLabel }}</span>
          <span class="project-name-tag" @click.stop>{{ pet.context?.active_project?.name || '未选择项目' }}</span>
          
          <!-- 忽略/删除当前失败信息按钮 -->
          <button
            v-if="pet.latestFailedTask"
            type="button"
            class="ignore-btn-mini"
            title="隐藏/忽略此错误"
            @click.stop="pet.ignoreFailedTask(pet.latestFailedTask.id)"
          >
            ×
          </button>
        </div>
        <div class="status-detail-desc">{{ pet.statusDetail }}</div>
        <div v-if="pet.context?.running_tasks?.length" style="margin-top: 8px; display: flex; justify-content: flex-end;">
          <button
            type="button"
            class="action-pill-mini"
            style="background: #fef0f0; color: #f56c6c; border: 1px solid #fde2e2; padding: 4px 10px; font-size: 11px; border-radius: 4px; cursor: pointer; transition: all 0.2s;"
            @click.stop="handleAbortRunningTask()"
          >
            中止
          </button>
        </div>
      </div>

      <!-- 紧凑型诊断中心 -->
      <div class="diagnose-box-compact">
        <div class="diagnose-header-row" @click="toggleDiagnoseCollapsed" style="cursor: pointer; user-select: none;">
          <div style="display: flex; align-items: center; gap: 6px;">
            <span class="collapse-arrow" :class="{ open: !diagnoseCollapsed }">▶</span>
            <span class="diagnose-title-text">🩺 系统诊断</span>
          </div>
          <button
            type="button"
            class="scan-btn-mini"
            :disabled="pet.diagnoseLoading"
            @click.stop="pet.runDiagnose()"
          >
            {{ pet.diagnoseLoading ? '诊断中...' : '重新诊断' }}
          </button>
        </div>

        <div v-show="!diagnoseCollapsed" class="diagnose-body-wrapper">
          <!-- 正常状态 -->
          <div
            v-if="!pet.diagnoseLoading && (!pet.diagnoseResult || pet.diagnoseResult.issues.length === 0)"
            class="diagnose-healthy-mini"
          >
            <span class="icon-healthy-mini">✓</span>
            <span>系统健康状态良好。</span>
          </div>

          <!-- 异常状态列表 -->
          <div v-else-if="!pet.diagnoseLoading && pet.diagnoseResult" class="diagnose-list-mini">
            <div
              v-for="(issue, index) in pet.diagnoseResult.issues"
              :key="index"
              class="diagnose-item-mini"
              :class="issue.level"
            >
              <span class="issue-bullet">•</span>
              <span class="issue-msg-mini">{{ issue.message }}</span>
            </div>

            <!-- 推荐修复动作 -->
            <div v-if="pet.diagnoseResult.suggestions.length" class="suggestions-box-mini">
              <div class="suggestion-actions-mini">
                <button
                  v-for="(sug, idx) in pet.diagnoseResult.suggestions"
                  :key="idx"
                  type="button"
                  class="action-pill-mini"
                  @click="handleActionClick(sug)"
                >
                  {{ sug.label }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <p class="status-scope-hint">待处理修章与续跑以章节维护为准，任务日志在日志中心；山山负责说明与指路。</p>

      <!-- 快捷动作导航：单行排列 -->
      <section class="quick-actions-compact">
        <button
          type="button"
          class="nav-btn-compact"
          :class="{ primary: pet.novelBatchPaused }"
          @click="navigate('/chapters/maintenance')"
        >
          <span>🔧 修章</span>
        </button>
        <button type="button" class="nav-btn-compact" @click="navigate('/logs')">
          <span>📑 日志</span>
        </button>
        <button type="button" class="nav-btn-compact" @click="navigate('/config')">
          <span>⚙️ 配置</span>
        </button>
        <button type="button" class="nav-btn-compact" @click="navigate('/')">
          <span>🏠 主页</span>
        </button>
      </section>
    </section>

    <!-- 主体区域：AI 问答 -->
    <section v-else class="tab-content-chat">
      <div ref="chatContainer" class="chat-messages-compact" :title="SHANSHAN_CHAT_SCOPE">
        <div
          v-for="(msg, index) in pet.chatHistory"
          :key="index"
          class="chat-row"
          :class="msg.role"
        >
          <img
            v-if="msg.role === 'assistant'"
            class="msg-avatar"
            :src="avatar"
            alt=""
            draggable="false"
          />
          <div class="msg-stack">
            <span class="msg-sender">{{ msg.role === 'user' ? '你' : '山山' }}</span>
            <div
              class="msg-bubble"
              :class="{ welcome: index === 0 && msg.role === 'assistant' }"
            >
              <div class="msg-text" v-html="renderMarkdown(msg.content)" />
              <div v-if="msg.actions && msg.actions.length" class="msg-actions">
                <button
                  v-for="(act, aIdx) in msg.actions"
                  :key="aIdx"
                  type="button"
                  class="msg-action-btn"
                  @click="handleActionClick(act)"
                >
                  {{ act.label }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <div v-if="pet.chatLoading" class="chat-row assistant">
          <img class="msg-avatar" :src="avatar" alt="" draggable="false" />
          <div class="msg-stack">
            <span class="msg-sender">山山</span>
            <div class="msg-bubble loading-bubble" aria-label="正在回复">
              <span class="dot-bounce">.</span>
              <span class="dot-bounce">.</span>
              <span class="dot-bounce">.</span>
            </div>
          </div>
        </div>
      </div>

      <div v-if="pet.chatHistory.length <= 1 && !pet.chatLoading" class="chat-suggestions-strip">
        <button
          v-for="(q, qIdx) in suggestedQuestions"
          :key="qIdx"
          type="button"
          class="suggest-chip"
          @click="handleSuggestQuestion(q)"
        >
          {{ q }}
        </button>
      </div>

      <footer class="chat-composer-slim">
        <div class="chat-input-bar-compact">
          <button
            type="button"
            class="clear-chat-btn"
            title="清空会话"
            aria-label="清空会话"
            @click="pet.clearChatHistory()"
          >
            🗑️
          </button>
          <textarea
            ref="chatInputRef"
            v-model="inputMessage"
            class="chat-textarea"
            rows="1"
            :placeholder="SHANSHAN_CHAT_PLACEHOLDER"
            :disabled="pet.chatLoading"
            @keydown="handleInputKeydown"
          />
          <button
            type="button"
            class="send-chat-btn"
            :disabled="pet.chatLoading || !inputMessage.trim()"
            title="发送 (Enter)"
            @click="handleSend"
          >
            ↑
          </button>
        </div>
      </footer>
    </section>

    <!-- 状态指示页脚（对话页隐藏以留出发言区） -->
    <footer v-if="activeTab === 'status'" class="shell-footer-compact">
      <span class="sync-text-mini" :class="{ visible: pet.loading }" aria-live="polite">同步中...</span>
    </footer>
  </main>
</template>

<style scoped>
:global(html),
:global(body),
:global(#app) {
  width: 100%;
  height: 100%;
  min-width: 0;
  margin: 0;
  overflow: hidden;
  background: transparent;
}

/* 玻璃拟态极简高阶设计 */
.bubble-shell {
  width: 100vw;
  height: 100vh;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px;
  border: 1px solid rgba(220, 227, 237, 0.45);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  box-shadow: 0 16px 36px rgba(10, 24, 48, 0.16), 0 2px 10px rgba(10, 24, 48, 0.06);
  color: #2c3e50;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  user-select: none;
  overflow: hidden;
  font-size: 13px; /* 提升全局基础字号 */
}

/* 头部行合并设计 */
.bubble-header-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 32px;
  flex: none;
}

.header-left-brand {
  display: flex;
  align-items: center;
  gap: 8px;
}

.avatar-mini-wrap {
  position: relative;
  width: 28px;
  height: 28px;
  background: #f0f4f9;
  border-radius: 50%;
  padding: 1px;
  border: 1px solid rgba(0, 0, 0, 0.05);
}

.avatar-mini {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
}

.status-pulse-mini {
  position: absolute;
  bottom: -1px;
  right: -1px;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  border: 1.5px solid var(--color-bg-surface);
  background: #64d2ff;
}

.status-pulse-mini.working { background: #30b0c7; }
.status-pulse-mini.question { background: #e6a23c; }
.status-pulse-mini.success { background: #34c759; }
.status-pulse-mini.error { background: #ff3b30; }
.status-pulse-mini.offline { background: #8e8e93; }

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.header-left-brand strong {
  font-size: 15px;
  font-weight: 750;
  color: #1a202c;
}

.brand-sub {
  font-size: 10px;
  font-weight: 500;
  color: #909399;
}

/* 迷你 Tab 导航 */
.bubble-tabs-compact {
  display: flex;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 6px;
  padding: 1.5px;
}

.tab-btn-mini {
  border: 0;
  background: transparent;
  padding: 4px 14px;
  font-size: 13px;
  font-weight: 700;
  color: #718096;
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tab-btn-mini.active {
  background: var(--color-bg-surface);
  color: #1a202c;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}

/* 状态页布局 (严格禁止溢出与滚动) */
.tab-content-status {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  justify-content: space-between;
  overflow: hidden; /* 强制禁止滚动条 */
}

.batch-pause-banner {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 11px;
  border-radius: 8px;
  border: 1px solid #f5dab1;
  background: linear-gradient(180deg, #fdf6ec 0%, #fff 100%);
  cursor: pointer;
  flex: none;
}

.batch-pause-banner:hover {
  border-color: #e6a23c;
}

.batch-pause-icon {
  font-size: 12px;
  color: #e6a23c;
}

.batch-pause-text {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  color: #606266;
}

.batch-pause-cta {
  font-size: 11px;
  font-weight: 600;
  color: #b88230;
}

.status-scope-hint,
.chat-scope-hint {
  margin: 0;
  font-size: 11px;
  line-height: 1.4;
  color: #909399;
  flex: none;
}

.chat-scope-hint {
  padding: 1px 4px 5px;
  color: #7c8798;
  letter-spacing: 0.01em;
}

/* 状态卡片 */
.status-card-compact {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 11px;
  border: 1px solid #e4eaf2;
  border-radius: 8px;
  background: var(--color-bg-surface);
  flex: none;
}

.status-card-compact.clickable {
  cursor: pointer;
  transition: all 0.2s ease;
}

.status-card-compact.clickable:hover {
  border-color: rgba(0, 122, 255, 0.35);
  background: rgba(0, 122, 255, 0.02);
  box-shadow: 0 4px 12px rgba(0, 122, 255, 0.05);
}

.ignore-btn-mini {
  margin-left: 6px;
  border: none;
  background: transparent;
  color: #a0aec0;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.ignore-btn-mini:hover {
  background: rgba(0, 0, 0, 0.05);
  color: #e53e3e;
}

.status-title-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-indicator-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #48a868;
  box-shadow: 0 0 0 2px rgba(72, 168, 104, 0.14);
}

.status-indicator-dot.busy {
  background: #4f7fc6;
  box-shadow: 0 0 0 2px rgba(79, 127, 198, 0.14);
}

.status-indicator-dot.alert {
  background: #d65d5d;
  box-shadow: 0 0 0 2px rgba(214, 93, 93, 0.14);
}

.status-text-bold {
  font-size: 13.5px; /* 状态文本加大 */
  font-weight: 700;
  color: #1f2937;
}

.project-name-tag {
  margin-left: auto;
  font-size: 12px; /* 项目标签加大 */
  font-weight: 600;
  background: var(--color-border-subtle);
  color: #4a5568;
  padding: 1.5px 7px;
  border-radius: 4px;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-detail-desc {
  font-size: 12.5px; /* 描述文本加大 */
  color: #536176;
  line-height: 1.45;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

/* 诊断中心 */
.diagnose-box-compact {
  background: rgba(255, 255, 255, 0.65);
  border: 1px solid rgba(0, 0, 0, 0.05);
  border-radius: 8px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.diagnose-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex: none;
}

.diagnose-title-text {
  font-size: 13px; /* 诊断标题加大 */
  font-weight: 750;
  color: #4a5568;
}

.scan-btn-mini {
  border: 0;
  background: transparent;
  color: #007aff;
  font-size: 12px; /* 重新诊断按钮加大 */
  font-weight: 700;
  cursor: pointer;
  padding: 0;
}

.diagnose-healthy-mini {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #2f855a;
  background: #f0fff4;
  border: 1px solid #c6f6d5;
  padding: 6px 8px;
  border-radius: 6px;
  font-size: 12.5px; /* 健康信息字号加大 */
  flex: 1;
}

.icon-healthy-mini {
  font-weight: bold;
  font-size: 13px;
}

.diagnose-list-mini {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  overflow-y: auto;
}

.diagnose-item-mini {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  padding: 5px 8px;
  border-radius: 6px;
  font-size: 12px; /* 诊断项字号加大 */
  line-height: 1.4;
}

.diagnose-item-mini.error {
  background: #fff5f5;
  border: 1px solid #fed7d7;
  color: #c53030;
}

.diagnose-item-mini.warning {
  background: #fffaf0;
  border: 1px solid #feebc8;
  color: #dd6b20;
}

.issue-bullet {
  font-size: 14px;
  line-height: 1;
}

.issue-msg-mini {
  flex: 1;
}

.suggestions-box-mini {
  margin-top: 4px;
}

.suggestion-actions-mini {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.action-pill-mini {
  border: 1px solid #007aff;
  background: #e6f0ff;
  color: #007aff;
  padding: 2.5px 9px;
  border-radius: 12px;
  font-size: 11px; /* 修复建议字号加大 */
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-pill-mini:hover {
  background: #007aff;
  color: var(--color-bg-surface);
}

/* 导航栏一字排开 */
.quick-actions-compact {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
  flex: none;
}

.nav-btn-compact {
  height: 30px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 6px;
  background: var(--color-bg-surface);
  color: #2d3748;
  font-size: 12px; /* 快捷动作按钮加大 */
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.nav-btn-compact:hover {
  border-color: rgba(0, 0, 0, 0.15);
  background: #f7fafc;
}

.nav-btn-compact.primary {
  border-color: #e6a23c;
  background: #fdf6ec;
  color: #b88230;
}

.nav-btn-compact.primary:hover {
  background: #faecd8;
}

/* AI 聊天页布局 — 发言区优先占满剩余高度 */
.tab-content-chat {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow: hidden;
}

.chat-messages-compact {
  flex: 1 1 auto;
  min-height: 140px;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 6px 4px 6px 2px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  border-radius: 10px;
  background: linear-gradient(180deg, #f3f6fb 0%, var(--color-bg-surface-muted) 100%);
  border: 1px solid rgba(100, 120, 150, 0.12);
}

/* 消息滚动条定制 */
.chat-messages-compact::-webkit-scrollbar {
  width: 4px;
}
.chat-messages-compact::-webkit-scrollbar-track {
  background: transparent;
}
.chat-messages-compact::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.12);
  border-radius: 99px;
}

.chat-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  width: 100%;
}

.chat-row.user {
  flex-direction: row-reverse;
}

.msg-avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  flex-shrink: 0;
  object-fit: cover;
  border: 1px solid rgba(0, 0, 0, 0.06);
  background: var(--color-bg-surface);
}

.chat-row.user .msg-avatar {
  display: none;
}

.msg-stack {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-width: calc(100% - 34px);
  min-width: 0;
}

.chat-row.user .msg-stack {
  align-items: flex-end;
}

.msg-sender {
  font-size: 11px;
  font-weight: 700;
  color: #8a96a8;
  letter-spacing: 0.02em;
}

.chat-row.user .msg-sender {
  color: #5b8fd9;
}

.msg-bubble {
  max-width: 100%;
  padding: 8px 10px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.5;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  word-break: break-word;
}

.chat-row.assistant .msg-bubble {
  background: var(--color-bg-surface);
  border: 1px solid rgba(0, 0, 0, 0.07);
  border-top-left-radius: 4px;
  color: var(--color-text-strong);
}

.chat-row.assistant .msg-bubble.welcome {
  padding: 8px 10px;
  border-color: rgba(88, 132, 190, 0.2);
  background: linear-gradient(145deg, var(--color-bg-surface) 0%, #f0f6ff 100%);
  box-shadow: 0 4px 12px rgba(71, 104, 148, 0.08);
}

.chat-row.assistant .msg-bubble.welcome .msg-text {
  color: var(--color-text);
  line-height: 1.5;
  font-size: 13px;
}

.chat-row.user .msg-bubble {
  background: linear-gradient(135deg, #007aff 0%, #0062d1 100%);
  color: var(--color-bg-surface);
  border-top-right-radius: 4px;
  box-shadow: 0 4px 12px rgba(0, 122, 255, 0.28);
}

.msg-text :deep(strong) { font-weight: bold; }
.msg-text :deep(code) {
  font-family: ui-monospace, Consolas, monospace;
  background: rgba(0, 0, 0, 0.06);
  padding: 2px 5px;
  border-radius: 4px;
  font-size: 12.5px;
}

.chat-row.user .msg-text :deep(code) {
  background: rgba(255, 255, 255, 0.22);
}

.msg-text :deep(.md-list-item) {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  margin-top: 3px;
}

.msg-text :deep(.bullet) {
  color: #007aff;
  font-weight: bold;
}

.chat-row.user .msg-text :deep(.bullet) {
  color: var(--color-bg-surface);
}

/* 消息动作按钮 */
.msg-actions {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  border-top: 1px dashed rgba(0, 0, 0, 0.08);
  padding-top: 6px;
}

.msg-action-btn {
  border: 1px solid #007aff;
  background: transparent;
  color: #007aff;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
}

.msg-action-btn:hover {
  background: #007aff;
  color: var(--color-bg-surface);
}

/* Loading 气泡 */
.loading-bubble {
  display: flex;
  gap: 3px;
}

.dot-bounce {
  font-weight: bold;
  font-size: 14px;
  animation: bounce 1.4s infinite ease-in-out both;
}

.dot-bounce:nth-child(1) { animation-delay: -0.32s; }
.dot-bounce:nth-child(2) { animation-delay: -0.16s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1.0); }
}

.chat-suggestions-strip {
  flex: none;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  padding: 2px 0;
}

.chat-suggestions-strip::-webkit-scrollbar {
  display: none;
}

.suggest-chip {
  min-width: 0;
  border: 1px solid rgba(0, 122, 255, 0.16);
  background: var(--color-bg-surface);
  padding: 5px 8px;
  border-radius: 8px;
  font-size: 11.5px;
  line-height: 1.3;
  text-align: center;
  color: var(--color-text-muted);
  cursor: pointer;
  white-space: normal;
  word-break: break-word;
}

.suggest-chip:hover {
  border-color: rgba(0, 122, 255, 0.35);
  color: #007aff;
}

.chat-composer-slim {
  flex: none;
}

.clear-chat-btn {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  background: transparent;
  border: 0;
  font-size: 15px;
  line-height: 1;
  color: var(--color-text-subtle);
  cursor: pointer;
  border-radius: 6px;
  padding: 0;
}

.clear-chat-btn:hover {
  background: rgba(0, 0, 0, 0.05);
  color: var(--color-text-muted);
}

.chat-input-bar-compact {
  display: flex;
  gap: 6px;
  align-items: center;
  background: var(--color-bg-surface);
  border-radius: 10px;
  padding: 4px 6px;
  border: 1px solid rgba(105, 124, 151, 0.2);
  box-shadow: 0 2px 8px rgba(30, 52, 84, 0.05);
}

.chat-input-bar-compact:focus-within {
  border-color: rgba(0, 122, 255, 0.45);
  box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.1);
}

.chat-textarea {
  flex: 1;
  min-height: 26px;
  max-height: 72px;
  resize: none;
  background: transparent;
  border: 0;
  font-size: 13px;
  line-height: 1.4;
  color: var(--color-text-strong);
  padding: 4px 2px;
  outline: none;
  font-family: inherit;
}

.chat-textarea::placeholder {
  color: #a0aec0;
}

.send-chat-btn {
  border: 0;
  background: #007aff;
  color: var(--color-bg-surface);
  font-size: 15px;
  font-weight: 800;
  width: 30px;
  height: 30px;
  padding: 0;
  border-radius: 8px;
  cursor: pointer;
  flex-shrink: 0;
  line-height: 1;
}

.send-chat-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

/* 页脚样式 */
.shell-footer-compact {
  min-height: 14px;
  text-align: center;
  font-size: 11px; /* 页脚字号加大 */
  color: #a0aec0;
  padding-top: 2px;
  border-top: 1px solid rgba(0, 0, 0, 0.03);
  flex: none;
}

.sync-text-mini {
  opacity: 0;
  color: #3182ce;
  font-weight: 700;
  transition: opacity 0.2s ease;
}

.sync-text-mini.visible {
  opacity: 0.72;
}

.collapse-arrow {
  display: inline-block;
  font-size: 8px;
  color: #718096;
  transition: transform 0.2s ease;
  transform: rotate(0deg);
}

.collapse-arrow.open {
  transform: rotate(90deg);
}
</style>
