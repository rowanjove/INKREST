import { ref } from 'vue'
import type { usePetStore } from '../stores/pet'

export type PetEdge = 'left' | 'right' | 'top'

export type Bounds = { x: number; y: number; width: number; height: number }
export type WorkArea = { x: number; y: number; width: number; height: number }

/** 贴边后仍露出的可悬停探头区域（像素） */
export const PEEK_PX = 48
/** 距屏幕边缘保留的美观留白（像素） */
export const EDGE_MARGIN_PX = 8
/** 触发磁力靠齐的距离阈值（像素） */
export const MAGNETIC_SNAP_THRESHOLD = 28
/** 触发收纳隐藏的距离阈值（像素） */
export const DOCK_THRESHOLD = 14

/**
 * 分析当前窗口离屏幕哪一侧最近，以及是否越过边界
 */
export function analyzeEdgeProximity(bounds: Bounds, workArea: WorkArea): {
  edge: PetEdge
  distance: number
  isPushedOut: boolean
} {
  const dLeft = bounds.x - workArea.x
  const dRight = (workArea.x + workArea.width) - (bounds.x + bounds.width)
  const dTop = bounds.y - workArea.y

  const candidates: Array<{ edge: PetEdge; distance: number; isPushedOut: boolean }> = [
    { edge: 'left', distance: Math.abs(dLeft), isPushedOut: dLeft < -6 },
    { edge: 'right', distance: Math.abs(dRight), isPushedOut: dRight < -6 },
    { edge: 'top', distance: Math.abs(dTop), isPushedOut: dTop < -6 },
  ]

  candidates.sort((a, b) => a.distance - b.distance)
  return candidates[0]
}

/** 计算贴边隐藏（探头）位置 */
export function dockedPosition(edge: PetEdge, bounds: Bounds, workArea: WorkArea): { x: number; y: number } {
  const { width, height } = bounds
  const clampedY = Math.min(workArea.y + workArea.height - height, Math.max(workArea.y, bounds.y))
  const clampedX = Math.min(workArea.x + workArea.width - width, Math.max(workArea.x, bounds.x))

  switch (edge) {
    case 'left':
      return { x: workArea.x - width + PEEK_PX, y: clampedY }
    case 'right':
      return { x: workArea.x + workArea.width - PEEK_PX, y: clampedY }
    case 'top':
      return { x: clampedX, y: workArea.y - height + PEEK_PX }
  }
}

/** 计算磁力贴齐（保留留白且完全在屏幕内）位置 */
export function magneticSnapPosition(edge: PetEdge, bounds: Bounds, workArea: WorkArea): { x: number; y: number } {
  const { width, height } = bounds
  const clampedY = Math.min(workArea.y + workArea.height - height - EDGE_MARGIN_PX, Math.max(workArea.y + EDGE_MARGIN_PX, bounds.y))
  const clampedX = Math.min(workArea.x + workArea.width - width - EDGE_MARGIN_PX, Math.max(workArea.x + EDGE_MARGIN_PX, bounds.x))

  switch (edge) {
    case 'left':
      return { x: workArea.x + EDGE_MARGIN_PX, y: clampedY }
    case 'right':
      return { x: workArea.x + workArea.width - width - EDGE_MARGIN_PX, y: clampedY }
    case 'top':
      return { x: clampedX, y: workArea.y + EDGE_MARGIN_PX }
  }
}

export function clampToWorkArea(pos: { x: number; y: number }, bounds: Bounds, workArea: WorkArea) {
  return {
    x: Math.min(workArea.x + workArea.width - bounds.width, Math.max(workArea.x, Math.round(pos.x))),
    y: Math.min(workArea.y + workArea.height - bounds.height, Math.max(workArea.y, Math.round(pos.y))),
  }
}

/**
 * 桌宠窗口贴边收纳与磁吸控制：
 * 1. 靠近边缘松手磁力贴齐（完整显示在屏幕内）
 * 2. 推过屏幕边缘松手平滑滑入收纳（露出探头挂件）
 * 3. 悬停探头平滑滑出，离开延时平滑滑回
 */
export function usePetEdgeDock(pet: ReturnType<typeof usePetStore>) {
  const expandedPosition = ref<{ x: number; y: number } | null>(null)
  const revealedEdge = ref<PetEdge | null>(null)

  async function readBounds(): Promise<{ bounds: Bounds; workArea: WorkArea } | null> {
    const api = window.electronAPI
    if (!api?.getPetWindowBounds || !api?.getPetWorkArea) return null
    const bounds = await api.getPetWindowBounds()
    const workArea = await api.getPetWorkArea()
    if (!bounds || !workArea) return null
    return { bounds, workArea }
  }

  async function moveTo(pos: { x: number; y: number }, durationMs = 220) {
    const api = window.electronAPI
    if (api?.animatePetWindowBounds) {
      await api.animatePetWindowBounds(pos, durationMs)
    } else if (api?.setPetWindowBounds) {
      await api.setPetWindowBounds(pos)
    }
  }

  /** 拖拽结束后检测是贴边收纳、磁吸贴齐还是自由停放 */
  async function applyEdgeDockIfNeeded() {
    const ctx = await readBounds()
    if (!ctx) return
    const { bounds, workArea } = ctx
    const analysis = analyzeEdgeProximity(bounds, workArea)

    // 1. 用户主动推到屏幕边缘外，或者距离边缘极近 -> 触发收纳探头
    if (analysis.isPushedOut || analysis.distance <= DOCK_THRESHOLD) {
      const edge = analysis.edge
      // 记录收纳前在屏幕内的展开锚点
      expandedPosition.value = magneticSnapPosition(edge, bounds, workArea)
      const target = dockedPosition(edge, bounds, workArea)
      pet.setHiddenAtEdge(edge)
      await moveTo(target, 220)
      await pet.updateSettings({
        dockedEdge: edge,
        position: expandedPosition.value,
      })
      return
    }

    // 2. 在屏幕内但靠近边缘 -> 磁吸贴齐，不隐藏探头
    if (analysis.distance <= MAGNETIC_SNAP_THRESHOLD) {
      const edge = analysis.edge
      const target = magneticSnapPosition(edge, bounds, workArea)
      await moveTo(target, 160)
      expandedPosition.value = null
      pet.setHiddenAtEdge(null)
      await pet.updateSettings({
        dockedEdge: null,
        position: target,
      })
      return
    }

    // 3. 自由停放在屏幕内部
    expandedPosition.value = null
    revealedEdge.value = null
    if (pet.isHiddenAtEdge) {
      pet.setHiddenAtEdge(null)
    }
    await pet.updateSettings({
      dockedEdge: null,
      position: { x: bounds.x, y: bounds.y },
    })
  }

  /** 悬停探头或需要展开时平滑滑出 */
  async function restoreFromEdge() {
    const ctx = await readBounds()
    if (!ctx) {
      pet.setHiddenAtEdge(null)
      revealedEdge.value = null
      return
    }
    const { bounds, workArea } = ctx
    const edge = (pet.isHiddenAtEdge as PetEdge | null) || revealedEdge.value
    if (!edge) return

    revealedEdge.value = edge
    let target = expandedPosition.value
    if (!target) {
      target = magneticSnapPosition(edge, bounds, workArea)
    } else {
      target = clampToWorkArea(target, bounds, workArea)
    }

    // 展开状态切换与平滑滑出
    pet.setHiddenAtEdge(null)
    await moveTo(target, 220)
  }

  /** 鼠标离开展开后的窗口且过了宽限期，平滑滑回边缘探头形态 */
  async function hideToRevealedEdgeIfNeeded() {
    const edge = revealedEdge.value
    if (!edge || pet.isHiddenAtEdge) return
    const ctx = await readBounds()
    if (!ctx) return
    const { bounds, workArea } = ctx
    const pos = dockedPosition(edge, bounds, workArea)
    pet.setHiddenAtEdge(edge)
    await moveTo(pos, 220)
  }

  function clearRevealedEdge() {
    revealedEdge.value = null
    expandedPosition.value = null
  }

  return {
    expandedPosition,
    revealedEdge,
    applyEdgeDockIfNeeded,
    restoreFromEdge,
    hideToRevealedEdgeIfNeeded,
    clearRevealedEdge,
  }
}
