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
  font-size: 13px;
}

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

.shell-footer-compact {
  min-height: 14px;
  text-align: center;
  font-size: 11px;
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
</style>