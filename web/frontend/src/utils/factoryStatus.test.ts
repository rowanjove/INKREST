import { describe, expect, it } from 'vitest'
import {
  factoryModeOptions,
  formatFactoryMode,
  formatFactoryState,
  getFactoryPrimaryAction,
  formatFactoryIntent,
  getFactoryTone,
} from './factoryStatus'
import type { FactoryDashboard } from '../types/factory'

const baseDashboard: FactoryDashboard = {
  project: { id: 'p1', name: '测试书', scale: 'medium', mode: 'newbie_auto' },
  production_plan: {
    status: 'ready',
    title: '测试书',
    selling_points: [],
    target_chapters: 100,
    planned_chapters: 10,
    readiness: { ok: 6, total: 6, missing: [] },
    next_steps: [],
  },
  factory_status: {
    state: 'ready',
    current_stage: 'planning',
    completed_chapters: 0,
    target_chapters: 100,
    running_tasks: 0,
    risk_level: 'low',
  },
  mode_profile: {
    mode: 'newbie_auto',
    label: '新手全自动',
    automation_level: 'high',
    priorities: ['自动补齐开书要素'],
    operator_hint: '适合从灵感直接推进。',
  },
  operator_brief: {
    severity: 'success',
    next_intent: 'run',
    summary: '生产条件已就绪',
    details: '可以继续生产。',
  },
  commands: [],
  pipeline: [],
  quality_summary: {
    status: 'missing',
    total_reports: 0,
    passed: 0,
    failed: 0,
    ai_flavor_risks: 0,
    latest_issue: null,
  },
  export_check: {
    status: 'blocked',
    can_export: false,
    blockers: [],
    warnings: [],
    route: '/workspace',
    primary_action: '进入导出',
  },
  repair: { blocked_count: 0, items: [] },
  exports: { txt_available: false, epub_available: false, pdf_available: false },
}

describe('factoryStatus', () => {
  it('formats factory modes', () => {
    expect(formatFactoryMode('newbie_auto')).toBe('新手全自动')
    expect(formatFactoryMode('author_copilot')).toBe('作者协作')
  })

  it('formats factory states', () => {
    expect(formatFactoryState('blocked')).toBe('等待修复')
    expect(formatFactoryState('running')).toBe('生产中')
  })

  it('maps blocked state to auto repair primary action', () => {
    const dashboard = {
      ...baseDashboard,
      factory_status: { ...baseDashboard.factory_status, state: 'blocked' as const },
    }
    expect(getFactoryPrimaryAction(dashboard)).toEqual({
      label: '自动修复',
      intent: 'repair',
    })
  })

  it('maps planning state to production-plan action', () => {
    const dashboard = {
      ...baseDashboard,
      factory_status: { ...baseDashboard.factory_status, state: 'planning' as const },
    }
    expect(getFactoryPrimaryAction(dashboard)).toEqual({
      label: '生成生产计划',
      intent: 'plan',
    })
  })

  it('maps risk levels to display tones', () => {
    expect(getFactoryTone('high')).toBe('danger')
    expect(getFactoryTone('medium')).toBe('warning')
    expect(getFactoryTone('low')).toBe('success')
  })

  it('lists factory modes in product priority order', () => {
    expect(factoryModeOptions().map((option) => option.value)).toEqual([
      'newbie_auto',
      'author_copilot',
      'platform_review',
      'longform_stable',
      'studio',
    ])
  })

  it('formats factory command intents for operator brief tags', () => {
    expect(formatFactoryIntent('create')).toBe('新建作品')
    expect(formatFactoryIntent('repair')).toBe('自动修复')
    expect(formatFactoryIntent('export')).toBe('导出检查')
  })
})
