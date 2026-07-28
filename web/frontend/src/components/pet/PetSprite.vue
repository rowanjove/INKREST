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
  if (props.state === 'hide-left') return { file: hideLeftPng, frames: 1, fps: 1 }
  if (props.state === 'hide-right') return { file: hideRightPng, frames: 1, fps: 1 }
  if (props.state === 'hide-top') return { file: hideTopPng, frames: 1, fps: 1 }
  if (props.state === 'hide-bottom') return { file: hideBottomPng, frames: 1, fps: 1 }
  if (props.state === 'success') return { file: successSheet, frames: 12, fps: 12, badge: successBadge }
  if (props.state === 'error') return { file: errorSheet, frames: 12, fps: 12, badge: errorBadge }
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
  <div class="pet-sprite-wrap" :style="fallbackStyle" aria-label="山山助手">
    <div class="pet-sprite" :style="spriteStyle" />
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
