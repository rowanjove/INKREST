import { describe, expect, it } from 'vitest'

import { CONFIG_SECTION_ALIASES, CONFIG_SECTIONS } from './configSections'

describe('task-based settings sections', () => {
  it('exposes six user-task groups in a stable order', () => {
    expect(CONFIG_SECTIONS.map((section) => section.id)).toEqual([
      'models-providers',
      'memory',
      'generation-quality',
      'writing-layout',
      'extensions',
      'system-data',
    ])
  })

  it('keeps legacy deep links mapped to their task group', () => {
    expect(CONFIG_SECTION_ALIASES).toMatchObject({
      appearance: 'system-data',
      models: 'models-providers',
      'embedding-config': 'memory',
      'pipeline-runtime': 'generation-quality',
      'writing-rules': 'writing-layout',
      'agent-bridge': 'extensions',
    })
  })
})
