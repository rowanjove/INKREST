<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import PetSprite from '../components/pet/PetSprite.vue'
import { usePetEdgeDock } from '../composables/usePetEdgeDock'
import { usePetStore } from '../stores/pet'

const pet = usePetStore()
const edgeDock = usePetEdgeDock(pet)
const dragging = ref(false)
const pointerStart = ref<{ x: number; y: number } | null>(null)
const moved = ref(false)
let clickTimer: number | null = null

async function onPointerDown(event: PointerEvent) {
  if (pet.isHiddenAtEdge) {
    await edgeDock.restoreFromEdge()
  }
  pointerStart.value = { x: event.screenX, y: event.screenY }
  moved.value = false
  dragging.value = true
  pet.setDragging(true)
  ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
}

async function onPointerMove(event: PointerEvent) {
  if (!dragging.value || !pointerStart.value) return
  const dx = event.screenX - pointerStart.value.x
  const dy = event.screenY - pointerStart.value.y
  if (Math.abs(dx) < 5 && Math.abs(dy) < 5) return
  moved.value = true
  pointerStart.value = { x: event.screenX, y: event.screenY }
  await window.electronAPI?.movePetBy?.({ x: dx, y: dy })
}

async function onPointerUp(event: PointerEvent) {
  dragging.value = false
  ;(event.currentTarget as HTMLElement).releasePointerCapture(event.pointerId)
  if (moved.value) {
    await edgeDock.applyEdgeDockIfNeeded()
    if (!pet.isHiddenAtEdge) {
      await window.electronAPI?.savePetPosition?.()
    }
  }
  pet.setDragging(false)
}

async function onMouseEnter() {
  if (pet.isHiddenAtEdge) {
    await edgeDock.restoreFromEdge()
  }
}

function onClick() {
  if (moved.value) return
  if (clickTimer) {
    window.clearTimeout(clickTimer)
    clickTimer = null
    window.electronAPI?.openMainWindow?.()
    return
  }
  clickTimer = window.setTimeout(() => {
    window.electronAPI?.togglePetBubble?.()
    clickTimer = null
  }, 180)
}

function onContextMenu(event: MouseEvent) {
  event.preventDefault()
  window.electronAPI?.showPetContextMenu?.()
}

onMounted(async () => {
  await pet.loadSettings()
  pet.startPolling()
})

onBeforeUnmount(() => {
  pet.stopPolling()
})
</script>

<template>
  <main class="pet-window" @contextmenu="onContextMenu">
    <button
      class="pet-hit-area"
      type="button"
      aria-label="山山助手"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @mouseenter="onMouseEnter"
      @click="onClick"
    >
      <PetSprite :state="pet.state" :size="pet.settings.size" />
    </button>
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

.pet-window {
  width: 100vw;
  height: 100vh;
  display: grid;
  place-items: center;
  background: transparent;
  pointer-events: none;
  user-select: none;
}

.pet-hit-area {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: grab;
  pointer-events: auto;
}

.pet-hit-area:active {
  cursor: grabbing;
}
</style>
