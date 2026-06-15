import { onBeforeUnmount, onMounted, ref } from 'vue'
import { usePetEdgeDock } from './usePetEdgeDock'
import { usePetStore } from '../stores/pet'

export function usePetWindowInteraction() {
  const pet = usePetStore()
  const edgeDock = usePetEdgeDock(pet)
  const dragging = ref(false)
  const pointerStart = ref<{ x: number; y: number } | null>(null)
  const moved = ref(false)
  const activePointerId = ref<number | null>(null)
  let clickTimer: number | null = null
  let hideTimer: number | null = null

  function ignorePointerButton(event: PointerEvent | MouseEvent) {
    event.preventDefault()
    event.stopPropagation()
  }

  function isPrimaryPointerButton(event: PointerEvent) {
    return event.isPrimary && event.button === 0
  }

  function clearHideTimer() {
    if (hideTimer) {
      window.clearTimeout(hideTimer)
      hideTimer = null
    }
  }

  async function onPointerDown(event: PointerEvent) {
    if (!isPrimaryPointerButton(event)) {
      if (event.button !== 2) {
        ignorePointerButton(event)
      }
      return
    }
    clearHideTimer()
    if (pet.isHiddenAtEdge) {
      await edgeDock.restoreFromEdge()
    }
    pointerStart.value = { x: event.screenX, y: event.screenY }
    moved.value = false
    dragging.value = true
    activePointerId.value = event.pointerId
    pet.setDragging(true)
    ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
  }

  async function onPointerMove(event: PointerEvent) {
    if (!dragging.value || !pointerStart.value || event.pointerId !== activePointerId.value) return
    const dx = event.screenX - pointerStart.value.x
    const dy = event.screenY - pointerStart.value.y
    if (Math.abs(dx) < 5 && Math.abs(dy) < 5) return
    moved.value = true
    pointerStart.value = { x: event.screenX, y: event.screenY }
    await window.electronAPI?.movePetBy?.({ x: dx, y: dy })
  }

  async function onPointerUp(event: PointerEvent) {
    if (event.pointerId !== activePointerId.value) return
    dragging.value = false
    activePointerId.value = null
    pointerStart.value = null
    if ((event.currentTarget as HTMLElement).hasPointerCapture(event.pointerId)) {
      ;(event.currentTarget as HTMLElement).releasePointerCapture(event.pointerId)
    }
    if (moved.value) {
      await edgeDock.applyEdgeDockIfNeeded()
      if (!pet.isHiddenAtEdge) {
        await window.electronAPI?.savePetPosition?.()
      }
    }
    pet.setDragging(false)
  }

  async function onMouseEnter() {
    clearHideTimer()
    if (pet.isHiddenAtEdge) {
      await edgeDock.restoreFromEdge()
    }
  }

  function onMouseLeave() {
    clearHideTimer()
    if (dragging.value) return
    hideTimer = window.setTimeout(() => {
      hideTimer = null
      void edgeDock.hideToRevealedEdgeIfNeeded()
    }, 420)
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

  function onMouseDown(event: MouseEvent) {
    if (event.button !== 0 && event.button !== 2) {
      ignorePointerButton(event)
    }
  }

  function onAuxClick(event: MouseEvent) {
    ignorePointerButton(event)
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
    clearHideTimer()
    pet.stopPolling()
  })

  return {
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
  }
}
