<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import type { AppTourStep } from '../composables/useAppTour'

const props = defineProps<{
  visible: boolean
  step: AppTourStep | null
  stepIndex: number
  totalSteps: number
}>()

const emit = defineEmits<{
  next: []
  prev: []
  skip: []
}>()

const highlightStyle = ref<Record<string, string>>({})
const cardStyle = ref<Record<string, string>>({})

function updateAnchor() {
  if (!props.visible || !props.step?.selector) {
    highlightStyle.value = { display: 'none' }
    cardStyle.value = {}
    return
  }
  const el = document.querySelector(props.step.selector) as HTMLElement | null
  if (!el) {
    highlightStyle.value = { display: 'none' }
    cardStyle.value = { top: '20%', left: '50%', transform: 'translateX(-50%)' }
    return
  }
  const rect = el.getBoundingClientRect()
  const pad = 8
  highlightStyle.value = {
    display: 'block',
    top: `${Math.max(8, rect.top - pad)}px`,
    left: `${Math.max(8, rect.left - pad)}px`,
    width: `${rect.width + pad * 2}px`,
    height: `${rect.height + pad * 2}px`,
  }
  const top = rect.bottom + 14
  cardStyle.value = {
    top: `${Math.min(top, window.innerHeight - 220)}px`,
    left: `${Math.min(Math.max(16, rect.left), window.innerWidth - 360)}px`,
  }
}

const progressLabel = computed(() => `${props.stepIndex + 1} / ${props.totalSteps}`)

let resizeHandler: (() => void) | null = null

watch(
  () => [props.visible, props.step?.id, props.stepIndex],
  async () => {
    await nextTick()
    updateAnchor()
  },
  { immediate: true },
)

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      resizeHandler = () => updateAnchor()
      window.addEventListener('resize', resizeHandler)
      window.addEventListener('scroll', resizeHandler, true)
    } else if (resizeHandler) {
      window.removeEventListener('resize', resizeHandler)
      window.removeEventListener('scroll', resizeHandler, true)
      resizeHandler = null
    }
  },
)

onBeforeUnmount(() => {
  if (resizeHandler) {
    window.removeEventListener('resize', resizeHandler)
    window.removeEventListener('scroll', resizeHandler, true)
  }
})
</script>

<template>
  <div v-if="visible" class="app-tour-root">
    <div class="app-tour-mask" />
    <div class="app-tour-highlight" :style="highlightStyle" />
    <section class="app-tour-card" :style="cardStyle">
      <p class="app-tour-kicker">产品引导 {{ progressLabel }}</p>
      <h3>{{ step?.title }}</h3>
      <p class="app-tour-body">{{ step?.body }}</p>
      <div class="app-tour-actions">
        <el-button text @click="emit('skip')">跳过</el-button>
        <el-button :disabled="stepIndex <= 0" @click="emit('prev')">上一步</el-button>
        <el-button type="primary" @click="emit('next')">
          {{ stepIndex >= totalSteps - 1 ? '开始使用' : '下一步' }}
        </el-button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.app-tour-root {
  position: fixed;
  inset: 0;
  z-index: 5000;
  pointer-events: none;
}

.app-tour-mask {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  pointer-events: auto;
}

.app-tour-highlight {
  position: fixed;
  border: 2px solid #007aff;
  border-radius: 10px;
  box-shadow: 0 0 0 9999px rgba(15, 23, 42, 0.45);
  pointer-events: none;
  transition: all 0.2s ease;
}

.app-tour-card {
  position: fixed;
  width: min(340px, calc(100vw - 32px));
  padding: 14px;
  border-radius: 10px;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.2);
  pointer-events: auto;
}

.app-tour-kicker {
  margin: 0 0 4px;
  font-size: 11px;
  font-weight: 700;
  color: var(--color-text-muted);
}

h3 {
  margin: 0 0 6px;
  font-size: 16px;
}

.app-tour-body {
  margin: 0 0 12px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--color-text-muted);
}

.app-tour-actions {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
}
</style>