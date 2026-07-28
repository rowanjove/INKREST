import { describe, expect, it } from 'vitest'
import {
  buildModelSavePayload,
  createEmptyModelForm,
  entryToModelForm,
  filterAvailablePresets,
  presetToModelForm,
  type ModelLibraryEntry,
  type ModelLibraryPreset,
} from './modelLibraryForm'

describe('modelLibraryForm', () => {
  const preset: ModelLibraryPreset = {
    id: 'openai-main',
    name: 'OpenAI Main',
    provider: 'openai',
    brand: 'OpenAI',
    base_url: 'https://api.openai.com/v1',
    model: 'gpt-5.2',
    max_tokens: 8192,
    temperature: 0.7,
    timeout: 120,
    description: 'main model',
  }

  it('creates a stable empty form default', () => {
    expect(createEmptyModelForm()).toMatchObject({
      id: '',
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
      slot: '',
    })
  })

  it('converts presets to editable form state without carrying API keys', () => {
    expect(presetToModelForm({ ...preset, type: 'image' })).toMatchObject({
      id: 'openai-main',
      name: 'OpenAI Main',
      api_key: '',
      has_api_key: false,
      type: 'image',
      slot: '',
    })
  })

  it('converts saved entries to edit form state while preserving stored-key hint', () => {
    const entry: ModelLibraryEntry = {
      id: 'local-main',
      name: '',
      provider: '',
      base_url: 'http://localhost:11434/v1',
      model: 'qwen3:14b',
      max_tokens: 0,
      temperature: undefined as unknown as number,
      timeout: 0,
      proxy: '',
      api_key: '',
      has_api_key: true,
      slot: 'daily',
    }

    expect(entryToModelForm(entry)).toMatchObject({
      id: 'local-main',
      name: 'local-main',
      provider: 'openai',
      max_tokens: 8192,
      temperature: 0.7,
      timeout: 120,
      has_api_key: true,
      slot: 'daily',
    })
  })

  it('removes UI-only fields from save payload and returns selected slot separately', () => {
    const form = { ...presetToModelForm(preset), has_api_key: true, slot: 'reasoning' as const }

    const result = buildModelSavePayload(form)

    expect(result.slot).toBe('reasoning')
    expect(result.payload).not.toHaveProperty('has_api_key')
    expect(result.payload).not.toHaveProperty('slot')
    expect(result.payload.id).toBe('openai-main')
  })

  it('filters presets that already exist or have been hidden', () => {
    const available = filterAvailablePresets({
      presets: [preset, { ...preset, id: 'local-main' }],
      models: [{ ...presetToModelForm(preset), id: 'openai-main' }],
      hiddenPresetIds: ['local-main'],
    })

    expect(available).toEqual([])
  })
})
