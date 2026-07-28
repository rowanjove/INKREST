<script setup lang="ts">
import PetSprite from '../components/pet/PetSprite.vue'
import { usePetWindowInteraction } from '../composables/usePetWindowInteraction'

const {
  pet,
  onPointerDown,
  onPointerMove,
  onPointerUp,
  onMouseDown,
  onAuxClick,
  onMouseEnter,
  onMouseLeave,
  onClick,
  onContextMenu,
} = usePetWindowInteraction()
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
      @mousedown="onMouseDown"
      @auxclick="onAuxClick"
      @mouseenter="onMouseEnter"
      @mouseleave="onMouseLeave"
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
