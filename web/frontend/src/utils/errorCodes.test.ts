import { describe, expect, it } from 'vitest'
import { formatFailureDetail, normalizeFailureDetail } from './errorCodes'

describe('errorCodes failure formatting', () => {
  it('formats backend detail objects with hint and action metadata', () => {
    const detail = normalizeFailureDetail({
      code: 'LLM_TIMEOUT',
      detail: '模型请求超时',
      hint: '可重试单章或降低并发。',
      retryable: true,
      user_action: 'retry_or_reduce_concurrency',
      resumable_from: 'writer',
    })

    expect(detail.code).toBe('LLM_TIMEOUT')
    expect(detail.retryable).toBe(true)
    expect(detail.user_action).toBe('retry_or_reduce_concurrency')
    expect(detail.resumable_from).toBe('writer')
    expect(formatFailureDetail(detail)).toContain('模型请求超时')
    expect(formatFailureDetail(detail)).toContain('可重试单章或降低并发。')
  })

  it('falls back to known code hints for task failure payloads', () => {
    const detail = normalizeFailureDetail({
      failure_kind: 'LLM_RATE_LIMIT',
      message: 'too many requests',
      retryable: true,
      user_action: 'retry_later_or_switch_model',
    })

    expect(detail.code).toBe('LLM_RATE_LIMIT')
    expect(formatFailureDetail(detail)).toContain('too many requests')
    expect(formatFailureDetail(detail)).toContain('模型 API 触发限流')
  })
})
