import { onBeforeUnmount, onMounted, ref } from 'vue'
import { usePetEdgeDock } from './usePetEdgeDock'
import { usePetStore } from '../stores/pet'

export function usePetWindowInteraction() {
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

  return {
    pet,
    onPointerDown,
    onPointerMove,
    onPointerUp,
    onMouseEnter,
    onClick,
    onContextMenu,
  }
}