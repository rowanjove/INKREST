import { ref } from 'vue'
import type { usePetStore } from '../stores/pet'

type PetEdge = 'left' | 'right' | 'top' | 'bottom'

type Bounds = { x: number; y: number; width: number; height: number }
type WorkArea = { x: number; y: number; width: number; height: number }

/** 距工作区边缘小于该值时触发贴边收纳 */
const EDGE_SNAP_PX = 18
/** 贴边后仍露出的可悬停区域（像素） */
const PEEK_PX = 52

function detectNearestEdge(bounds: Bounds, workArea: WorkArea): PetEdge | null {
  const dLeft = bounds.x - workArea.x
  const dRight = workArea.x + workArea.width - (bounds.x + bounds.width)
  const dTop = bounds.y - workArea.y
  const dBottom = workArea.y + workArea.height - (bounds.y + bounds.height)
  const distances: Array<{ edge: PetEdge; d: number }> = [
    { edge: 'left', d: dLeft },
    { edge: 'right', d: dRight },
    { edge: 'top', d: dTop },
    { edge: 'bottom', d: dBottom },
  ]
  const nearest = distances.reduce((best, cur) => (cur.d < best.d ? cur : best))
  if (nearest.d > EDGE_SNAP_PX) return null
  return nearest.edge
}

function dockedPosition(edge: PetEdge, bounds: Bounds, workArea: WorkArea): { x: number; y: number } {
  const { width, height } = bounds
  switch (edge) {
    case 'left':
      return { x: workArea.x - width + PEEK_PX, y: bounds.y }
    case 'right':
      return { x: workArea.x + workArea.width - PEEK_PX, y: bounds.y }
    case 'top':
      return { x: bounds.x, y: workArea.y - height + PEEK_PX }
    case 'bottom':
      return { x: bounds.x, y: workArea.y + workArea.height - PEEK_PX }
  }
}

function clampToWorkArea(pos: { x: number; y: number }, bounds: Bounds, workArea: WorkArea) {
  return {
    x: Math.min(workArea.x + workArea.width - bounds.width, Math.max(workArea.x, Math.round(pos.x))),
    y: Math.min(workArea.y + workArea.height - bounds.height, Math.max(workArea.y, Math.round(pos.y))),
  }
}

/**
 * 桌宠窗口贴边自动隐藏：拖到屏幕边缘后只露出一条边，鼠标悬停恢复。
 */
export function usePetEdgeDock(pet: ReturnType<typeof usePetStore>) {
  const expandedPosition = ref<{ x: number; y: number } | null>(null)

  async function readBounds(): Promise<{ bounds: Bounds; workArea: WorkArea } | null> {
    const api = window.electronAPI
    if (!api?.getPetWindowBounds || !api?.getPetWorkArea) return null
    const bounds = await api.getPetWindowBounds()
    const workArea = await api.getPetWorkArea()
    if (!bounds || !workArea) return null
    return { bounds, workArea }
  }

  /** 拖拽结束后检测是否应贴边收纳 */
  async function applyEdgeDockIfNeeded() {
    const ctx = await readBounds()
    if (!ctx) return
    const { bounds, workArea } = ctx
    const edge = detectNearestEdge(bounds, workArea)
    if (!edge) {
      if (pet.isHiddenAtEdge) {
        await restoreFromEdge()
      }
      expandedPosition.value = null
      return
    }

    expandedPosition.value = { x: bounds.x, y: bounds.y }
    const pos = dockedPosition(edge, bounds, workArea)
    await window.electronAPI?.setPetWindowBounds?.(pos)
    pet.setHiddenAtEdge(edge)
  }

  /** 悬停或开始拖拽时从贴边状态展开 */
  async function restoreFromEdge() {
    const ctx = await readBounds()
    if (!ctx) {
      pet.setHiddenAtEdge(null)
      return
    }
    const { bounds, workArea } = ctx
    const edge = pet.isHiddenAtEdge
    let target = expandedPosition.value
    if (!target && edge) {
      const peek = dockedPosition(edge, bounds, workArea)
      target = clampToWorkArea(
        {
          x: edge === 'left' ? workArea.x + 8 : edge === 'right' ? workArea.x + workArea.width - bounds.width - 8 : peek.x,
          y: edge === 'top' ? workArea.y + 8 : edge === 'bottom' ? workArea.y + workArea.height - bounds.height - 8 : peek.y,
        },
        bounds,
        workArea,
      )
    } else if (target) {
      target = clampToWorkArea(target, bounds, workArea)
    }
    if (target) {
      await window.electronAPI?.setPetWindowBounds?.(target)
    }
    expandedPosition.value = null
    pet.setHiddenAtEdge(null)
    await window.electronAPI?.savePetPosition?.()
  }

  return {
    expandedPosition,
    applyEdgeDockIfNeeded,
    restoreFromEdge,
  }
}