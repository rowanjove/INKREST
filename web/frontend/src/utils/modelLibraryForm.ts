import type { ModelSlot } from '../constants/modelSlots'

export interface ModelLibraryEntry {
  id: string
  name: string
  provider: string
  base_url: string
  model: string
  max_tokens: number
  temperature: number
  timeout: number
  proxy: string
  api_key: string
  has_api_key?: boolean
  type?: string
  slot?: ModelSlot
}

export interface ModelLibraryPreset {
  id: string
  name: string
  provider: string
  brand: string
  base_url: string
  model: string
  max_tokens: number
  temperature: number
  timeout: number
  description: string
  local?: boolean
  type?: string
}

export interface ModelLibraryForm {
  id: string
  name: string
  provider: string
  base_url: string
  api_key: string
  has_api_key: boolean
  model: string
  max_tokens: number
  temperature: number
  timeout: number
  proxy: string
  type: string
  slot: ModelSlot
}

export function createEmptyModelForm(): ModelLibraryForm {
  return {
    id: '',
    name: '',
    provider: 'openai',
    base_url: '',
    api_key: '',
    has_api_key: false,
    model: '',
    max_tokens: 8192,
    temperature: 0.7,
    timeout: 120,
    proxy: '',
    type: 'text',
    slot: '' as ModelSlot,
  }
}

export function presetToModelForm(preset: ModelLibraryPreset): ModelLibraryForm {
  return {
    id: preset.id,
    name: preset.name,
    provider: preset.provider,
    base_url: preset.base_url,
    api_key: '',
    has_api_key: false,
    model: preset.model,
    max_tokens: preset.max_tokens,
    temperature: preset.temperature,
    timeout: preset.timeout,
    proxy: '',
    type: preset.type || 'text',
    slot: '' as ModelSlot,
  }
}

export function entryToModelForm(entry: ModelLibraryEntry): ModelLibraryForm {
  return {
    id: entry.id,
    name: entry.name || entry.id,
    provider: entry.provider || 'openai',
    base_url: entry.base_url,
    api_key: '',
    has_api_key: Boolean(entry.has_api_key),
    model: entry.model,
    max_tokens: entry.max_tokens || 8192,
    temperature: entry.temperature ?? 0.7,
    timeout: entry.timeout || 120,
    proxy: entry.proxy || '',
    type: entry.type || 'text',
    slot: (entry.slot || '') as ModelSlot,
  }
}

export function buildModelSavePayload(form: ModelLibraryForm): {
  payload: Omit<ModelLibraryForm, 'has_api_key' | 'slot'>
  slot: ModelSlot
} {
  const payload = { ...form }
  const slot = (form.slot || '') as ModelSlot
  delete (payload as { has_api_key?: boolean }).has_api_key
  delete (payload as { slot?: ModelSlot }).slot
  return { payload, slot }
}

export function filterAvailablePresets({
  presets,
  models,
  hiddenPresetIds,
}: {
  presets: ModelLibraryPreset[]
  models: Pick<ModelLibraryEntry, 'id'>[]
  hiddenPresetIds: string[]
}): ModelLibraryPreset[] {
  const existingIds = new Set(models.map((m) => m.id))
  const hiddenPresets = new Set(hiddenPresetIds)
  return presets.filter((preset) => !existingIds.has(preset.id) && !hiddenPresets.has(preset.id))
}
