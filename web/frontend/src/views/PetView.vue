<script setup lang="ts">
import PetSprite from '../components/pet/PetSprite.vue'
import { usePetWindowInteraction } from '../composables/usePetWindowInteraction'

const {
  pet,
  pokeText,
  isPoked,
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
    <transition name="pop-fade">
      <div v-if="pokeText" class="pet-thought-bubble">
        {{ pokeText }}
      </div>
    </transition>
    <button
      class="pet-hit-area"
      :class="{
        'is-poked': isPoked,
        'is-docked': Boolean(pet.isHiddenAtEdge),
        [`docked-${pet.isHiddenAtEdge}`]: Boolean(pet.isHiddenAtEdge),
      }"
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
  position: relative;
  background: transparent;
  pointer-events: none;
  user-select: none;
}

.pet-thought-bubble {
  position: absolute;
  top: 4px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(88, 132, 190, 0.35);
  border-radius: 12px;
  padding: 4px 10px;
  font-size: 11.5px;
  line-height: 1.35;
  color: #1f3b64;
  box-shadow: 0 4px 14px rgba(10, 24, 48, 0.16);
  white-space: nowrap;
  pointer-events: none;
  z-index: 10;
  max-width: 92%;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pet-thought-bubble::after {
  content: '';
  position: absolute;
  bottom: -5px;
  left: 50%;
  transform: translateX(-50%);
  border-width: 5px 5px 0;
  border-style: solid;
  border-color: rgba(255, 255, 255, 0.94) transparent transparent;
}

.pop-fade-enter-active,
.pop-fade-leave-active {
  transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.pop-fade-enter-from,
.pop-fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(6px) scale(0.9);
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
  transition: transform 0.2s ease;
}

.pet-hit-area:active {
  cursor: grabbing;
}

.pet-hit-area.is-docked {
  cursor: pointer;
  filter: drop-shadow(0 0 6px rgba(64, 128, 224, 0.4));
  transition: filter 0.25s ease, transform 0.2s ease;
}

.pet-hit-area.is-docked:hover {
  filter: drop-shadow(0 0 12px rgba(64, 128, 224, 0.8));
}

.pet-hit-area.is-poked {
  animation: pet-bounce 0.35s ease;
}

@keyframes pet-bounce {
  0% { transform: scale(1); }
  40% { transform: scale(0.92, 1.08); }
  75% { transform: scale(1.05, 0.95); }
  100% { transform: scale(1); }
}
</style>

