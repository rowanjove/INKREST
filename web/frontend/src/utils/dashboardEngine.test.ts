import { describe, expect, it } from 'vitest'
import { formatModelLabel, inferNextChapterId, resolveEngine } from './dashboardEngine'

describe('inferNextChapterId', () => {
  it('returns 001 for empty list', () => {
    expect(inferNextChapterId([])).toBe('001')
  })

  it('pads next id after max chapter', () => {
    expect(inferNextChapterId([{ chapter_id: '009' }, { chapter_id: '011' }])).toBe('012')
  })

  it('ignores non-numeric chapter ids', () => {
    expect(inferNextChapterId([{ chapter_id: 'abc' }, { chapter_id: '003' }])).toBe('004')
  })
})

describe('formatModelLabel', () => {
  it('includes model id when name missing', () => {
    expect(formatModelLabel({ id: 'daily', model: 'gpt-4' })).toBe('daily (gpt-4)')
  })
})

describe('resolveEngine', () => {
  const models = [{ id: 'daily', name: '日常模型', model: 'glm-4', provider: 'openai', has_api_key: true }]

  it('prefers daily_model_id', () => {
    expect(
      resolveEngine({ llm: { daily_model_id: 'daily' } }, models),
    ).toEqual({ ready: true, label: '日常模型 (glm-4)', route: 'daily_model_id' })
  })

  it('falls back to llm.default provider', () => {
    expect(
      resolveEngine({ llm: { default: { provider: 'openai', model: 'gpt-4o', api_key: 'test-key' } } }, []),
    ).toEqual({ ready: true, label: 'gpt-4o', route: 'llm.default' })
  })

  it('returns static when nothing configured', () => {
    expect(resolveEngine({ llm: { provider: 'static' } }, [])).toEqual({
      ready: false,
      label: '未配置可用模型',
      route: 'static',
    })
  })

  it('rejects a remote model that has no configured api key', () => {
    expect(
      resolveEngine(
        { llm: { daily_model_id: 'remote' } },
        [{ id: 'remote', provider: 'openai', base_url: 'https://api.deepseek.com/v1', has_api_key: false }],
      ),
    ).toEqual({ ready: false, label: '未配置可用模型', route: 'credentials' })
  })

  it('allows a loopback model without an api key', () => {
    expect(
      resolveEngine(
        { llm: { daily_model_id: 'local' } },
        [{ id: 'local', provider: 'openai', base_url: 'http://127.0.0.1:11434/v1', has_api_key: false }],
      ),
    ).toEqual({ ready: true, label: 'local', route: 'daily_model_id' })
  })
})
