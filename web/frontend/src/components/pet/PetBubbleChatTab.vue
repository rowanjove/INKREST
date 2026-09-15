<script setup lang="ts">
import { computed } from 'vue'
import { ElIcon } from 'element-plus'
import { Delete, Promotion, Reading, EditPen } from '@element-plus/icons-vue'
import { usePetStore } from '../../stores/pet'
import { SHANSHAN_CHAT_PLACEHOLDER, SHANSHAN_CHAT_SCOPE } from '../../constants/shanshanCopy'
import type { PetAction } from '../../composables/usePetBubbleView'

defineProps<{
  avatar: string
  inputMessage: string
  suggestedQuestions: readonly string[]
  setChatContainer: (el: HTMLElement | null) => void
  setChatInputRef: (el: HTMLTextAreaElement | null) => void
  renderMarkdown: (text: string) => string
  onInputKeydown: (event: KeyboardEvent) => void
  onSend: () => void
  onSuggestQuestion: (q: string) => void
  onActionClick: (action: PetAction) => void
}>()

const emit = defineEmits<{
  'update:inputMessage': [value: string]
}>()

const pet = usePetStore()
const hasStreamingMessage = computed(() => pet.chatHistory.some((m) => m.streaming))
</script>

<template>
  <section class="tab-content-chat">
    <div
      :ref="(el) => setChatContainer(el as HTMLElement | null)"
      class="chat-messages-compact"
      :title="SHANSHAN_CHAT_SCOPE"
    >
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
            <span v-if="msg.streaming" class="streaming-cursor">▍</span>
            <div v-if="msg.chips && msg.chips.length" class="msg-chips-row">
              <span class="chips-label">参考：</span>
              <span v-for="(chip, cIdx) in msg.chips" :key="cIdx" class="context-chip">
                {{ chip.label }}
              </span>
            </div>
            <div v-if="msg.citations && msg.citations.length" class="msg-citations-box">
              <div class="citations-title">
                <el-icon class="box-icon"><Reading /></el-icon>
                <span>事实出处</span>
              </div>
              <div v-for="(cit, citIdx) in msg.citations" :key="citIdx" class="citation-item">
                <span class="citation-name">{{ cit.title }}</span>
                <span v-if="cit.snippet" class="citation-snippet">{{ cit.snippet }}</span>
              </div>
            </div>
            <div v-if="msg.patch" class="msg-patch-card">
              <div class="patch-header">
                <span class="patch-head-label">
                  <el-icon class="box-icon"><EditPen /></el-icon>
                  <span>修改提议</span>
                </span>
                <span class="patch-status-tag">{{ msg.patch.status || '待采纳' }}</span>
              </div>
              <div v-if="msg.patch.reason" class="patch-reason">{{ msg.patch.reason }}</div>
              <div class="patch-proposed">{{ msg.patch.proposed_text }}</div>
            </div>
            <div v-if="msg.actions && msg.actions.length" class="msg-actions">
              <button
                v-for="(act, aIdx) in msg.actions"
                :key="aIdx"
                type="button"
                class="msg-action-btn"
                @click="onActionClick(act)"
              >
                {{ act.label }}
              </button>
            </div>
            <div v-if="msg.suggestions && msg.suggestions.length && !pet.chatLoading" class="msg-suggestions">
              <button
                v-for="(sug, sIdx) in msg.suggestions"
                :key="sIdx"
                type="button"
                class="sug-pill-btn"
                @click="onSuggestQuestion(sug)"
              >
                {{ sug }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div v-if="pet.chatLoading && !hasStreamingMessage" class="chat-row assistant">
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
        @click="onSuggestQuestion(q)"
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
          <el-icon :size="14"><Delete /></el-icon>
        </button>
        <textarea
          :ref="(el) => setChatInputRef(el as HTMLTextAreaElement | null)"
          :value="inputMessage"
          class="chat-textarea"
          rows="1"
          :placeholder="SHANSHAN_CHAT_PLACEHOLDER"
          :disabled="pet.chatLoading"
          @input="emit('update:inputMessage', ($event.target as HTMLTextAreaElement).value)"
          @keydown="onInputKeydown"
        />
        <button
          type="button"
          class="send-chat-btn"
          :disabled="pet.chatLoading || !inputMessage.trim()"
          title="发送 (Enter)"
          @click="onSend"
        >
          <el-icon :size="14"><Promotion /></el-icon>
        </button>
      </div>
    </footer>
  </section>
</template>

<style scoped>
.tab-content-chat {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow: hidden;
}

.chat-messages-compact {
  flex: 1 1 auto;
  min-height: 140px;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  border-radius: var(--radius-md, 10px);
  background: var(--color-bg-app, #f7f9fc);
  border: 1px solid var(--color-border-subtle, #e8edf3);
}

.chat-messages-compact::-webkit-scrollbar {
  width: 5px;
}

.chat-messages-compact::-webkit-scrollbar-track {
  background: transparent;
}

.chat-messages-compact::-webkit-scrollbar-thumb {
  background: rgba(100, 116, 139, 0.2);
  border-radius: 99px;
}

.chat-messages-compact::-webkit-scrollbar-thumb:hover {
  background: rgba(100, 116, 139, 0.35);
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
  width: 28px;
  height: 28px;
  border-radius: 50%;
  flex-shrink: 0;
  object-fit: cover;
  border: 1.5px solid var(--color-bg-surface, #ffffff);
  box-shadow: 0 2px 4px rgba(15, 23, 42, 0.08);
  background: var(--color-bg-surface);
}

.chat-row.user .msg-avatar {
  display: none;
}

.msg-stack {
  display: flex;
  flex-direction: column;
  gap: 3px;
  max-width: calc(100% - 38px);
  min-width: 0;
}

.chat-row.user .msg-stack {
  align-items: flex-end;
}

.msg-sender {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-muted, #8a96a8);
  letter-spacing: 0.02em;
  padding: 0 4px;
}

.chat-row.user .msg-sender {
  color: var(--color-primary, #c66f4f);
}

.msg-bubble {
  max-width: 100%;
  padding: 9px 12px;
  border-radius: 12px;
  font-size: 12.5px;
  line-height: 1.55;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
  word-break: break-word;
}

.chat-row.assistant .msg-bubble {
  background: var(--color-bg-surface, #ffffff);
  border: 1px solid var(--color-border, #e2e8f0);
  border-top-left-radius: 4px;
  color: var(--color-text, #1f2937);
}

.chat-row.assistant .msg-bubble.welcome {
  padding: 10px 12px;
  border-color: rgba(198, 111, 79, 0.22);
  background: linear-gradient(150deg, var(--color-bg-surface, #ffffff) 0%, var(--color-primary-soft, #fff5f0) 100%);
  box-shadow: 0 3px 10px rgba(198, 111, 79, 0.06);
}

.chat-row.assistant .msg-bubble.welcome .msg-text {
  color: var(--color-text, #1f2937);
  line-height: 1.55;
  font-size: 12.5px;
}

.chat-row.user .msg-bubble {
  background: linear-gradient(135deg, var(--color-primary, #c66f4f) 0%, #ad5a3d 100%);
  color: #ffffff;
  border-top-right-radius: 4px;
  box-shadow: 0 3px 10px rgba(198, 111, 79, 0.25);
}

.msg-text :deep(p) {
  margin: 0 0 6px;
}

.msg-text :deep(p:last-child) {
  margin-bottom: 0;
}

.msg-text :deep(strong) {
  font-weight: 700;
}

.msg-text :deep(code) {
  font-family: ui-monospace, Consolas, monospace;
  background: rgba(0, 0, 0, 0.06);
  padding: 2px 5px;
  border-radius: 4px;
  font-size: 12px;
}

.chat-row.user .msg-text :deep(code) {
  background: rgba(255, 255, 255, 0.24);
  color: #ffffff;
}

.msg-text :deep(.md-list-item) {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-top: 4px;
}

.msg-text :deep(.bullet) {
  color: var(--color-primary, #c66f4f);
  font-weight: bold;
}

.chat-row.user .msg-text :deep(.bullet) {
  color: #ffffff;
}

.box-icon {
  margin-right: 4px;
  vertical-align: -1px;
}

.msg-actions {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  border-top: 1px dashed var(--color-border, #e2e8f0);
  padding-top: 6px;
}

.msg-action-btn {
  border: 1px solid var(--color-primary, #c66f4f);
  background: var(--color-primary-soft, #fff5f0);
  color: var(--color-primary, #c66f4f);
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 11.5px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.18s ease;
}

.msg-action-btn:hover {
  background: var(--color-primary, #c66f4f);
  color: #ffffff;
}

.streaming-cursor {
  display: inline-block;
  color: var(--color-primary, #c66f4f);
  font-weight: bold;
  animation: blink 0.8s infinite;
  margin-left: 2px;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.msg-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px dashed var(--color-border, #e2e8f0);
}

.sug-pill-btn {
  font-size: 11px;
  padding: 3px 9px;
  border-radius: 99px;
  border: 1px solid var(--color-border, #d9e1ec);
  background: var(--color-bg-surface, #ffffff);
  color: var(--color-text, #334155);
  cursor: pointer;
  transition: all 0.18s ease;
}

.sug-pill-btn:hover {
  background: var(--color-primary-soft, #fff5f0);
  color: var(--color-primary, #c66f4f);
  border-color: var(--color-primary, #c66f4f);
}

.loading-bubble {
  display: flex;
  gap: 4px;
  align-items: center;
  padding: 6px 12px;
}

.dot-bounce {
  font-weight: bold;
  font-size: 16px;
  line-height: 1;
  color: var(--color-primary, #c66f4f);
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

.suggest-chip {
  min-width: 0;
  border: 1px solid var(--color-border, #e2e8f0);
  background: var(--color-bg-surface, #ffffff);
  padding: 6px 8px;
  border-radius: var(--radius-sm, 7px);
  font-size: 11px;
  line-height: 1.35;
  text-align: center;
  color: var(--color-text-muted, #64748b);
  cursor: pointer;
  white-space: normal;
  word-break: break-word;
  transition: all 0.18s ease;
}

.suggest-chip:hover {
  border-color: var(--color-primary, #c66f4f);
  color: var(--color-primary, #c66f4f);
  background: var(--color-primary-soft, #fff5f0);
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
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-subtle, #94a3b8);
  cursor: pointer;
  border-radius: 6px;
  padding: 0;
  transition: all 0.18s ease;
}

.clear-chat-btn:hover {
  background: #fee2e2;
  color: #ef4444;
}

.chat-input-bar-compact {
  display: flex;
  gap: 6px;
  align-items: center;
  background: var(--color-bg-surface, #ffffff);
  border-radius: var(--radius-md, 10px);
  padding: 4px 8px;
  border: 1px solid var(--color-border, #d6dee8);
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
  transition: all 0.18s ease;
}

.chat-input-bar-compact:focus-within {
  border-color: var(--color-primary, #c66f4f);
  box-shadow: 0 0 0 3px var(--color-primary-muted, rgba(198, 111, 79, 0.14));
}

.chat-textarea {
  flex: 1;
  min-height: 26px;
  max-height: 72px;
  resize: none;
  background: transparent;
  border: 0;
  font-size: 12.5px;
  line-height: 1.45;
  color: var(--color-text-strong, #0f172a);
  padding: 4px 2px;
  outline: none;
  font-family: inherit;
}

.chat-textarea::placeholder {
  color: var(--color-text-subtle, #94a3b8);
}

.send-chat-btn {
  border: 0;
  background: var(--color-primary, #c66f4f);
  color: #ffffff;
  width: 28px;
  height: 28px;
  padding: 0;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.18s ease;
}

.send-chat-btn:hover:not(:disabled) {
  background: var(--color-primary-hover, #ad5f43);
  transform: translateY(-1px);
}

.send-chat-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.msg-chips-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px dashed var(--color-border, #e2e8f0);
}

.chips-label {
  font-size: 11px;
  color: var(--color-text-subtle, #718096);
}

.context-chip {
  font-size: 10.5px;
  background: var(--color-primary-soft, #fff5f0);
  color: var(--color-primary, #c66f4f);
  border: 1px solid rgba(198, 111, 79, 0.2);
  border-radius: 4px;
  padding: 1px 6px;
}

.msg-citations-box {
  margin-top: 8px;
  padding: 8px 10px;
  background: var(--color-bg-app, #f8fafc);
  border: 1px solid var(--color-border-subtle, #edf0f4);
  border-radius: 6px;
  font-size: 11px;
}

.citations-title {
  font-weight: 600;
  color: var(--color-text-strong, #1f2937);
  margin-bottom: 4px;
  display: flex;
  align-items: center;
}

.citation-item {
  margin-top: 4px;
  display: flex;
  flex-direction: column;
}

.citation-name {
  color: var(--color-primary, #c66f4f);
  font-weight: 500;
}

.citation-snippet {
  color: var(--color-text-muted, #64748b);
  font-size: 10px;
  margin-top: 1px;
  line-height: 1.35;
}

.msg-patch-card {
  margin-top: 8px;
  padding: 8px 10px;
  background: rgba(22, 163, 74, 0.06);
  border-left: 3px solid #16a34a;
  border-radius: 6px;
}

.patch-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  font-weight: 600;
  color: #15803d;
}

.patch-head-label {
  display: flex;
  align-items: center;
}

.patch-status-tag {
  font-size: 10px;
  background: #16a34a;
  color: white;
  padding: 1px 5px;
  border-radius: 3px;
}

.patch-reason {
  font-size: 11px;
  color: var(--color-text, #334155);
  margin-top: 4px;
}

.patch-proposed {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.5;
  background: var(--color-bg-surface, #ffffff);
  padding: 6px 8px;
  border-radius: 4px;
  border: 1px solid var(--color-border, #e2e8f0);
  white-space: pre-wrap;
}
</style>