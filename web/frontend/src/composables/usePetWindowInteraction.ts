import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { usePetEdgeDock } from './usePetEdgeDock'
import { usePetStore } from '../stores/pet'

export function usePetWindowInteraction() {
  const pet = usePetStore()
  const edgeDock = usePetEdgeDock(pet)
  const dragging = ref(false)
  const pointerStart = ref<{ x: number; y: number } | null>(null)
  const moved = ref(false)
  const activePointerId = ref<number | null>(null)
  const pokeText = ref<string>('')
  const isPoked = ref<boolean>(false)

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

  let clickTimer: number | null = null
  let hideTimer: number | null = null
  let hoverEnterTimer: number | null = null
  let pokeClearTimer: number | null = null

  // 拖拽 RAF 累积批处理，避免 await 阻塞导致的掉帧
  let pendingDeltaX = 0
  let pendingDeltaY = 0
  let rafHandle: number | null = null

  function scheduleMove() {
    if (rafHandle !== null) return
    rafHandle = window.requestAnimationFrame(() => {
      rafHandle = null
      if (pendingDeltaX !== 0 || pendingDeltaY !== 0) {
        const dx = pendingDeltaX
        const dy = pendingDeltaY
        pendingDeltaX = 0
        pendingDeltaY = 0
        void window.electronAPI?.movePetBy?.({ x: dx, y: dy })
      }
    })
  }

  function flushImmediateMove() {
    if (rafHandle !== null) {
      window.cancelAnimationFrame(rafHandle)
      rafHandle = null
    }
    if (pendingDeltaX !== 0 || pendingDeltaY !== 0) {
      const dx = pendingDeltaX
      const dy = pendingDeltaY
      pendingDeltaX = 0
      pendingDeltaY = 0
      void window.electronAPI?.movePetBy?.({ x: dx, y: dy })
    }
  }

  function triggerPoke() {
    pokeText.value = pet.getPokeReactionLine?.() || '在呢在呢，盯稿中～'
    isPoked.value = true
    if (pokeClearTimer) window.clearTimeout(pokeClearTimer)
    pokeClearTimer = window.setTimeout(() => {
      pokeText.value = ''
      isPoked.value = false
      pokeClearTimer = null
    }, 2800)
  }

  function ignorePointerButton(event: PointerEvent | MouseEvent) {
    event.preventDefault()
    event.stopPropagation()
  }

  function isPrimaryPointerButton(event: PointerEvent) {
    return event.isPrimary && event.button === 0
  }

  function clearTimers() {
    if (hideTimer) {
      window.clearTimeout(hideTimer)
      hideTimer = null
    }
    if (hoverEnterTimer) {
      window.clearTimeout(hoverEnterTimer)
      hoverEnterTimer = null
    }
  }

  async function onPointerDown(event: PointerEvent) {
    if (!isPrimaryPointerButton(event)) {
      if (event.button !== 2) {
        ignorePointerButton(event)
      }
      return
    }
    clearTimers()

    // 如果处于贴边隐藏态，点击按下时先展开
    if (pet.isHiddenAtEdge) {
      await edgeDock.restoreFromEdge()
    }

    pointerStart.value = { x: event.screenX, y: event.screenY }
    moved.value = false
    dragging.value = true
    activePointerId.value = event.pointerId
    pendingDeltaX = 0
    pendingDeltaY = 0
    pet.setDragging(true)
    ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
  }

  function onPointerMove(event: PointerEvent) {
    if (!dragging.value || !pointerStart.value || event.pointerId !== activePointerId.value) return
    const dx = event.screenX - pointerStart.value.x
    const dy = event.screenY - pointerStart.value.y
    if (dx === 0 && dy === 0) return

    pointerStart.value = { x: event.screenX, y: event.screenY }
    pendingDeltaX += dx
    pendingDeltaY += dy
    moved.value = true
    scheduleMove()
  }

  async function onPointerUp(event: PointerEvent) {
    if (event.pointerId !== activePointerId.value) return
    flushImmediateMove()

    dragging.value = false
    activePointerId.value = null
    pointerStart.value = null

    if ((event.currentTarget as HTMLElement).hasPointerCapture(event.pointerId)) {
      ;(event.currentTarget as HTMLElement).releasePointerCapture(event.pointerId)
    }

    if (moved.value) {
      await edgeDock.applyEdgeDockIfNeeded()
    }
    pet.setDragging(false)
  }

  function onMouseEnter() {
    clearTimers()

    // 若当前为贴边收纳态，采用 90ms 意图检测，防误触掠过，确认停留后平滑滑出
    if (pet.isHiddenAtEdge) {
      hoverEnterTimer = window.setTimeout(() => {
        hoverEnterTimer = null
        void edgeDock.restoreFromEdge()
      }, 90)
    }
  }

  function onMouseLeave() {
    if (hoverEnterTimer) {
      window.clearTimeout(hoverEnterTimer)
      hoverEnterTimer = null
    }
    if (dragging.value) return

    // 鼠标移出展开后的窗口，给予 500ms 宽限时间缓冲，防止边缘抽搐
    if (edgeDock.revealedEdge.value && !pet.isHiddenAtEdge) {
      hideTimer = window.setTimeout(() => {
        hideTimer = null
        void edgeDock.hideToRevealedEdgeIfNeeded()
      }, 500)
    }
  }

  function onClick() {
    if (moved.value) return
    triggerPoke()
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
    clearTimers()
    if (rafHandle !== null) {
      window.cancelAnimationFrame(rafHandle)
      rafHandle = null
    }
    if (clickTimer) window.clearTimeout(clickTimer)
    if (pokeClearTimer) window.clearTimeout(pokeClearTimer)
    pet.stopPolling()
  })

  return {
    pet,
    edgeDock,
    pokeText,
    isPoked,
    triggerPoke,
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

