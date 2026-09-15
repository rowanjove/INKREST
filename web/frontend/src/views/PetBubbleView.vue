<script setup lang="ts">
import { onBeforeUnmount, onMounted } from 'vue'
import PetBubbleStatusTab from '../components/pet/PetBubbleStatusTab.vue'
import PetBubbleChatTab from '../components/pet/PetBubbleChatTab.vue'
import { usePetBubbleView } from '../composables/usePetBubbleView'

const {
  pet,
  avatar,
  activeTab,
  inputMessage,
  diagnoseCollapsed,
  suggestedQuestions,
  toggleDiagnoseCollapsed,
  navigate,
  handleStatusCardClick,
  openMonitorForBatch,
  selectTab,
  handleInputKeydown,
  handleSend,
  handleSuggestQuestion,
  handleActionClick,
  handleFactoryIntent,
  handleFactoryRepair,
  handleAbortRunningTask,
  setChatContainer,
  setChatInputRef,
  renderMarkdown,
} = usePetBubbleView()

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

    <PetBubbleStatusTab
      v-if="activeTab === 'status'"
      :diagnose-collapsed="diagnoseCollapsed"
      :on-toggle-diagnose-collapsed="toggleDiagnoseCollapsed"
      :on-status-card-click="handleStatusCardClick"
      :on-open-monitor-for-batch="openMonitorForBatch"
      :on-navigate="navigate"
      :on-action-click="handleActionClick"
      :on-factory-intent="handleFactoryIntent"
      :on-factory-repair="handleFactoryRepair"
      :on-abort-running-task="handleAbortRunningTask"
    />

    <PetBubbleChatTab
      v-else
      :avatar="avatar"
      v-model:input-message="inputMessage"
      :suggested-questions="suggestedQuestions"
      :set-chat-container="setChatContainer"
      :set-chat-input-ref="setChatInputRef"
      :render-markdown="renderMarkdown"
      :on-input-keydown="handleInputKeydown"
      :on-send="handleSend"
      :on-suggest-question="handleSuggestQuestion"
      :on-action-click="handleActionClick"
    />

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

.bubble-shell {
  width: 100vw;
  height: 100vh;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid rgba(215, 224, 235, 0.75);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  box-shadow: 0 16px 40px rgba(10, 24, 48, 0.14), 0 2px 10px rgba(10, 24, 48, 0.04);
  color: var(--color-text, #1f2937);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  user-select: none;
  overflow: hidden;
  font-size: 13px;
}

.bubble-header-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 36px;
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
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 1.5px solid var(--color-bg-surface, #ffffff);
  background: #16a34a;
}

.status-pulse-mini.pulse-active { background: var(--color-primary, #c66f4f); }
.status-pulse-mini.pulse-error { background: #dc2626; }
.status-pulse-mini.working { background: var(--color-primary, #c66f4f); }
.status-pulse-mini.question { background: #e6a23c; }
.status-pulse-mini.success { background: #16a34a; }
.status-pulse-mini.error { background: #dc2626; }
.status-pulse-mini.offline { background: #94a3b8; }

.brand-text {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.header-left-brand strong {
  font-size: 14px;
  font-weight: 750;
  color: var(--color-text-strong, #0f172a);
}

.brand-sub {
  font-size: 10.5px;
  font-weight: 500;
  color: var(--color-text-muted, #64748b);
}

.bubble-tabs-compact {
  display: flex;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 7px;
  padding: 2px;
  gap: 2px;
}

.tab-btn-mini {
  border: 0;
  background: transparent;
  padding: 3px 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted, #64748b);
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.18s ease;
}

.tab-btn-mini.active {
  background: var(--color-bg-surface, #ffffff);
  color: var(--color-primary, #c66f4f);
  font-weight: 700;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.shell-footer-compact {
  min-height: 14px;
  text-align: center;
  font-size: 11px;
  color: var(--color-text-subtle, #94a3b8);
  padding-top: 2px;
  border-top: 1px solid rgba(0, 0, 0, 0.04);
  flex: none;
}

.sync-text-mini {
  opacity: 0;
  color: var(--color-primary, #c66f4f);
  font-weight: 700;
  transition: opacity 0.2s ease;
}

.sync-text-mini.visible {
  opacity: 0.85;
}
</style>