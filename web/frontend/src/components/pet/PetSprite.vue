<script setup lang="ts">
import { computed } from 'vue'
import type { PetState } from '../../stores/pet'

const props = withDefaults(defineProps<{
  state: PetState
  size?: number
}>(), {
  size: 180,
})

const idleSheet = new URL('../../assets/pet/shanshan/animations/idle_sheet.webp', import.meta.url).href
const workingSheet = new URL('../../assets/pet/shanshan/animations/working_sheet.webp', import.meta.url).href
const successSheet = new URL('../../assets/pet/shanshan/animations/success_sheet.webp', import.meta.url).href
const errorSheet = new URL('../../assets/pet/shanshan/animations/error_sheet.webp', import.meta.url).href
const fallbackPng = new URL('../../assets/pet/shanshan/static/idle_256.png', import.meta.url).href
const successBadge = new URL('../../assets/pet/shanshan/ui/success_badge.png', import.meta.url).href
const errorBadge = new URL('../../assets/pet/shanshan/ui/error_badge.png', import.meta.url).href

const draggingPng = new URL('../../assets/pet/shanshan/static/dragging.png', import.meta.url).href
const questionPng = new URL('../../assets/pet/shanshan/static/question.png', import.meta.url).href
const hideLeftPng = new URL('../../assets/pet/shanshan/static/hide_left.png', import.meta.url).href
const hideRightPng = new URL('../../assets/pet/shanshan/static/hide_right.png', import.meta.url).href
const hideTopPng = new URL('../../assets/pet/shanshan/static/hide_top.png', import.meta.url).href
const hideBottomPng = new URL('../../assets/pet/shanshan/static/hide_bottom.png', import.meta.url).href

interface SpriteConfig {
  file: string
  frames: number
  fps: number
  badge?: string
}

const stateConfig = computed<SpriteConfig>(() => {
  if (props.state === 'working') return { file: workingSheet, frames: 24, fps: 12 }
  if (props.state === 'dragging') return { file: draggingPng, frames: 1, fps: 1 }
  if (props.state === 'question') return { file: questionPng, frames: 1, fps: 1 }
  if (props.state === 'error') return { file: errorSheet, frames: 12, fps: 12, badge: errorBadge }
  if (props.state === 'hide-left') return { file: hideLeftPng, frames: 1, fps: 1 }
  if (props.state === 'hide-right') return { file: hideRightPng, frames: 1, fps: 1 }
  if (props.state === 'hide-top') return { file: hideTopPng, frames: 1, fps: 1 }
  if (props.state === 'hide-bottom') return { file: hideBottomPng, frames: 1, fps: 1 }
  if (props.state === 'success') return { file: successSheet, frames: 12, fps: 12, badge: successBadge }
  if (props.state === 'offline') return { file: errorSheet, frames: 12, fps: 8 }
  return { file: idleSheet, frames: 24, fps: 12 }
})

const spriteStyle = computed(() => {
  const config = stateConfig.value
  const scale = props.size / 256
  const baseScale = 0.82
  return {
    width: '256px',
    height: '256px',
    backgroundImage: `url("${config.file}")`,
    backgroundSize: config.frames > 1 ? `${256 * config.frames}px 256px` : '256px 256px',
    '--sheet-offset': `${-256 * config.frames}px`,
    animationName: config.frames > 1 ? 'pet-frames' : 'none',
    animationDuration: `${config.frames / config.fps}s`,
    animationTimingFunction: `steps(${config.frames})`,
    transform: props.state === 'dragging'
      ? `translate(-50%, -50%) scale(${scale * baseScale * 1.12}) rotate(5deg)`
      : `translate(-50%, -50%) scale(${scale * baseScale})`,
  }
})

const fallbackStyle = computed(() => ({
  width: `${props.size}px`,
  height: `${props.size}px`,
}))
</script>

<template>
  <div
    class="pet-sprite-wrap"
    :class="{
      'is-working': props.state === 'working',
      'is-docked': props.state.startsWith('hide-'),
    }"
    :style="fallbackStyle"
    aria-label="山山助手"
  >
    <div class="pet-sprite" :style="spriteStyle" />
    <!-- 工作态创作微标记（柔和跳动三连点） -->
    <div v-if="props.state === 'working'" class="working-sparkle" title="正在落笔创作中">
      <span class="sparkle-dot dot-1" />
      <span class="sparkle-dot dot-2" />
      <span class="sparkle-dot dot-3" />
    </div>
    <img v-if="stateConfig.badge" class="pet-status-badge" :src="stateConfig.badge" alt="" draggable="false" />
    <img class="pet-fallback" :src="fallbackPng" alt="" draggable="false" />
  </div>
</template>

<style scoped>
.pet-sprite-wrap {
  position: relative;
  overflow: visible;
  user-select: none;
  -webkit-user-drag: none;
  transition: filter 0.3s ease;
}

.pet-sprite-wrap.is-working .pet-sprite {
  animation: pet-frames steps(24) 2s infinite, pet-working-glow 2.4s ease-in-out infinite alternate;
}

.pet-sprite {
  position: absolute;
  top: 50%;
  left: 50%;
  background-repeat: no-repeat;
  image-rendering: auto;
  animation-name: pet-frames;
  animation-iteration-count: infinite;
  transform-origin: center center;
}

.working-sparkle {
  position: absolute;
  top: 6%;
  right: 12%;
  display: flex;
  align-items: center;
  gap: 3px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(88, 140, 240, 0.35);
  border-radius: 12px;
  padding: 3px 6px;
  box-shadow: 0 3px 10px rgba(32, 64, 128, 0.18);
  pointer-events: none;
  z-index: 5;
  animation: sparkle-float 2s ease-in-out infinite;
}

.sparkle-dot {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: #3b82f6;
  animation: sparkle-bounce 1.2s ease-in-out infinite;
}

.sparkle-dot.dot-2 {
  animation-delay: 0.2s;
  background: #60a5fa;
}

.sparkle-dot.dot-3 {
  animation-delay: 0.4s;
  background: #93c5fd;
}

@keyframes sparkle-bounce {
  0%, 80%, 100% {
    transform: scale(0.8);
    opacity: 0.5;
  }
  40% {
    transform: scale(1.35);
    opacity: 1;
  }
}

@keyframes sparkle-float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-4px);
  }
}

@keyframes pet-working-glow {
  0% {
    filter: drop-shadow(0 0 6px rgba(78, 140, 255, 0.4));
  }
  100% {
    filter: drop-shadow(0 0 16px rgba(120, 180, 255, 0.8));
  }
}

.pet-fallback {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  opacity: 0;
  pointer-events: none;
}

.pet-status-badge {
  position: absolute;
  top: 3%;
  right: 3%;
  width: 30%;
  height: 30%;
  object-fit: contain;
  filter: drop-shadow(0 2px 3px rgb(32 48 72 / 28%));
  pointer-events: none;
}

@keyframes pet-frames {
  from {
    background-position-x: 0;
  }
  to {
    background-position-x: var(--sheet-offset);
  }
}
</style>
