<script setup lang="ts">
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
          🗑️
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
          ↑
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
</style>