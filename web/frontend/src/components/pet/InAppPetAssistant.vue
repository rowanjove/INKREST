<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Minus } from '@element-plus/icons-vue'
import { usePetStore } from '../../stores/pet'
import PetSprite from './PetSprite.vue'
import PetBubbleStatusTab from './PetBubbleStatusTab.vue'
import PetBubbleChatTab from './PetBubbleChatTab.vue'
import { usePetBubbleView } from '../../composables/usePetBubbleView'

const pet = usePetStore()
const isElectron = computed(() => Boolean(window.electronAPI))

watch(
  () => pet.settings.enabled,
  async (newVal) => {
    if (!isElectron.value) {
      if (newVal) {
        await pet.refreshContext()
        await pet.runDiagnose()
        pet.startPolling()
      } else {
        pet.stopPolling()
        bubbleOpen.value = false
      }
    }
  },
)

const {
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

const bubbleOpen = ref(false)
const pokeText = ref('')
const isPoked = ref(false)
let pokeClearTimer: number | null = null

watch(
  () => pet.edgeAlertMessage,
  (msg) => {
    if (msg) {
      pokeText.value = msg
      isPoked.value = true
      if (pokeClearTimer) window.clearTimeout(pokeClearTimer)
      pokeClearTimer = window.setTimeout(() => {
        pokeText.value = ''
        isPoked.value = false
        pokeClearTimer = null
      }, 4200)
    }
  },
)

function handlePoke() {
  pokeText.value = pet.getPokeReactionLine?.() || '在呢在呢，盯稿中～'
  isPoked.value = true
  if (pokeClearTimer) window.clearTimeout(pokeClearTimer)
  pokeClearTimer = window.setTimeout(() => {
    pokeText.value = ''
    isPoked.value = false
    pokeClearTimer = null
  }, 3000)
}

function handleMascotClick() {
  handlePoke()
  bubbleOpen.value = !bubbleOpen.value
}

function handleOpenEvent() {
  bubbleOpen.value = true
  handlePoke()
}

onMounted(async () => {
  window.addEventListener('open-shanshan', handleOpenEvent)
  await pet.loadSettings()
  if (!isElectron.value && pet.settings.enabled) {
    await pet.refreshContext()
    await pet.runDiagnose()
    pet.startPolling()
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('open-shanshan', handleOpenEvent)
  if (!isElectron.value) {
    pet.stopPolling()
  }
  if (pokeClearTimer) window.clearTimeout(pokeClearTimer)
})
</script>

<template>
  <aside
    v-if="!isElectron && pet.settings.enabled"
    class="in-app-pet-container"
    aria-label="山山助手"
  >
    <transition name="bubble-slide">
      <div v-if="bubbleOpen" class="in-app-bubble-window">
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
          <div class="header-controls">
            <button
              type="button"
              class="win-btn-mini"
              title="收起对话"
              @click="bubbleOpen = false"
            >
              <el-icon><Minus /></el-icon>
            </button>
          </div>
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
      </div>
    </transition>

    <transition name="pop-fade">
      <div v-if="pokeText" class="in-app-thought-bubble">
        {{ pokeText }}
      </div>
    </transition>

    <button
      type="button"
      class="in-app-mascot-btn"
      :class="{ 'is-poked': isPoked, 'is-active': bubbleOpen }"
      title="山山（点击唤起助理气泡）"
      @click="handleMascotClick"
    >
      <PetSprite :state="pet.state" :size="108" />
    </button>
  </aside>
</template>

<style scoped>
.in-app-pet-container {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 2200;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  pointer-events: none;
}

.in-app-mascot-btn {
  pointer-events: auto;
  position: relative;
  width: 108px;
  height: 108px;
  background: transparent;
  border: 0;
  padding: 0;
  cursor: pointer;
  outline: none;
  filter: drop-shadow(0 6px 14px rgba(15, 23, 42, 0.22));
  transition: transform 0.22s cubic-bezier(0.34, 1.56, 0.64, 1);
  user-select: none;
}

.in-app-mascot-btn:hover {
  transform: translateY(-4px) scale(1.05);
}

.in-app-mascot-btn:active,
.in-app-mascot-btn.is-poked {
  transform: scale(0.95);
}

.in-app-thought-bubble {
  position: absolute;
  bottom: 114px;
  right: 12px;
  max-width: 240px;
  padding: 6px 12px;
  border: 1px solid rgba(88, 132, 190, 0.35);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(8px);
  color: #1f3b64;
  font-size: 12px;
  line-height: 1.4;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.16);
  pointer-events: none;
  white-space: nowrap;
  text-overflow: ellipsis;
  overflow: hidden;
  z-index: 2201;
}

.in-app-thought-bubble::after {
  content: '';
  position: absolute;
  bottom: -6px;
  right: 32px;
  border-width: 6px 6px 0 6px;
  border-style: solid;
  border-color: rgba(255, 255, 255, 0.96) transparent transparent transparent;
}

.in-app-bubble-window {
  pointer-events: auto;
  position: absolute;
  bottom: 120px;
  right: 0;
  width: 380px;
  height: 536px;
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(210, 220, 235, 0.7);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.98);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  box-shadow: 0 24px 50px -10px rgba(15, 23, 42, 0.18), 0 4px 16px -2px rgba(15, 23, 42, 0.06);
  overflow: hidden;
  z-index: 2205;
}

.bubble-header-bar {
  height: 48px;
  padding: 0 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  border-bottom: 1px solid var(--color-border-subtle, #edf0f4);
  background: var(--color-bg-surface-muted, #f8fafc);
  user-select: none;
  flex-shrink: 0;
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
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-mini {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  object-fit: cover;
  border: 1px solid rgba(0, 0, 0, 0.06);
}

.status-pulse-mini {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  border: 1.5px solid #fff;
  background: #16a34a;
}

.status-pulse-mini.pulse-active {
  background: var(--color-primary, #c66f4f);
  animation: pulse-ring 1.5s infinite;
}

.status-pulse-mini.pulse-error {
  background: #dc2626;
}

.brand-text {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.brand-text strong {
  font-size: 13.5px;
  font-weight: 750;
  color: var(--color-text-strong, #0f172a);
}

.brand-sub {
  font-size: 10.5px;
  color: var(--color-text-muted, #64748b);
}

.bubble-tabs-compact {
  display: flex;
  gap: 2px;
  padding: 3px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.05);
}

.tab-btn-mini {
  border: 0;
  background: transparent;
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--color-text-muted, #64748b);
  cursor: pointer;
  transition: all 0.16s ease;
}

.tab-btn-mini.active {
  background: #fff;
  color: var(--color-primary, #c66f4f);
  font-weight: 700;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.header-controls {
  display: flex;
  align-items: center;
}

.win-btn-mini {
  border: 0;
  background: transparent;
  width: 26px;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border-radius: 6px;
  color: var(--color-text-muted, #64748b);
  transition: all 0.16s ease;
}

.win-btn-mini:hover {
  background: rgba(0, 0, 0, 0.06);
  color: var(--color-text-strong, #0f172a);
}

.in-app-bubble-window :deep(.tab-content-status),
.in-app-bubble-window :deep(.tab-content-chat) {
  padding: 12px 14px;
}

.bubble-slide-enter-active,
.bubble-slide-leave-active {
  transition: all 0.24s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.bubble-slide-enter-from,
.bubble-slide-leave-to {
  opacity: 0;
  transform: translateY(16px) scale(0.96);
}

.pop-fade-enter-active,
.pop-fade-leave-active {
  transition: all 0.2s ease;
}

.pop-fade-enter-from,
.pop-fade-leave-to {
  opacity: 0;
  transform: translateY(6px);
}
</style>
