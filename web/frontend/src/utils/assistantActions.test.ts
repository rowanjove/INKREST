import { describe, expect, it } from 'vitest'

import { productionConfirmPath, sanitizePetAction } from './assistantActions'

describe('assistant action whitelist', () => {
  it('drops unknown types and external routes', () => {
    expect(sanitizePetAction({ type: 'wipe', label: '删库' })).toBeNull()
    expect(
      sanitizePetAction({ type: 'navigate', label: '外链', payload: { route: 'https://evil.test' } }),
    ).toBeNull()
  })

  it('turns generating actions into production confirmation routes', () => {
    const retry = sanitizePetAction({
      type: 'retry_task',
      label: '重试',
      payload: { chapter_id: '001' },
    })
    expect(retry).toMatchObject({
      type: 'navigate',
      payload: { route: '/production?intent=novel_continue&confirm=1' },
    })
    expect(productionConfirmPath('auto_repair_chapter', { chapter_id: '003' })).toBe(
      '/production?tab=reviews&chapter=003',
    )
  })
})
