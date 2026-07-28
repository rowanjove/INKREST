/** 文字模型全局档位（与 models.json slots 对齐） */

export type ModelSlot = '' | 'daily' | 'reasoning' | 'backup'

export const MODEL_SLOT_OPTIONS: Array<{ value: ModelSlot; label: string; hint: string }> = [
  { value: '', label: '空', hint: '不参与档位与 fallback' },
  { value: 'daily', label: '日常档', hint: '全书仅可指定 1 个，用于高频写作' },
  { value: 'reasoning', label: '逻辑档', hint: '全书仅可指定 1 个，用于规划与审校' },
  { value: 'backup', label: '备用', hint: '可多个，主模型失败时按顺序 fallback' },
]

export const modelSlotLabel = (slot: ModelSlot | string | undefined) =>
  MODEL_SLOT_OPTIONS.find((o) => o.value === (slot || ''))?.label || '空'

export const modelSlotTagType = (slot: ModelSlot | string | undefined) => {
  switch (slot) {
    case 'daily':
      return 'success'
    case 'reasoning':
      return 'warning'
    case 'backup':
      return 'info'
    default:
      return 'info'
  }
}