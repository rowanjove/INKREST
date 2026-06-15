import { describe, expect, it, beforeEach, vi } from 'vitest'
import { ref } from 'vue'
import type { FactoryDashboard } from '../types/factory'
import {
  readFactoryAdvancedExpanded,
  shouldAutoExpandFactoryAdvanced,
  useFactoryAdvancedView,
  writeFactoryAdvancedExpanded,
} from './useFactoryAdvancedView'

const baseDashboard: FactoryDashboard = {
  project: { id: 'p1', name: '测试书', scale: 'medium', mode: 'author_copilot' },
  production_plan: {
    status: 'ready',
    title: '测试书',
    selling_points: [],
    target_chapters: 80,
    planned_chapters: 10,
    readiness: { ok: 4, total: 4, missing: [] },
    next_steps: [],
  },
  factory_status: {
    state: 'ready',
    current_stage: 'planning',
    completed_chapters: 5,
    target_chapters: 80,
    running_tasks: 0,
    risk_level: 'low',
  },
  mode_profile: {
    mode: 'author_copilot',
    label: '作者协同',
    automation_level: 'balanced',
    priorities: [],
    operator_hint: '',
  },
  operator_brief: {
    severity: 'success',
    next_intent: 'run',
    summary: '可继续生产',
    details: '',
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
  stability_report: {
    status: 'missing',
    score: 0,
    summary: '',
    tracked: { characters: 0, foreshadows: 0, reader_promises: 0, secrets: 0 },
    risks: [],
    next_actions: [],
  },
  naturalness_report: {
    status: 'missing',
    score: 0,
    summary: '',
    risk_types: [],
    sample_issues: [],
    next_actions: [],
  },
  repair: { blocked_count: 0, items: [] },
  exports: { txt_available: false, epub_available: false, pdf_available: false },
}

describe('useFactoryAdvancedView', () => {
  const memory = new Map<string, string>()

  beforeEach(() => {
    memory.clear()
    vi.stubGlobal('localStorage', {
      getItem: (key: string) => memory.get(key) ?? null,
      setItem: (key: string, value: string) => {
        memory.set(key, value)
      },
      removeItem: (key: string) => {
        memory.delete(key)
      },
      clear: () => memory.clear(),
    })
  })

  it('defaults to collapsed when storage is empty', () => {
    expect(readFactoryAdvancedExpanded()).toBe(false)
  })

  it('persists expanded preference', () => {
    writeFactoryAdvancedExpanded(true)
    expect(readFactoryAdvancedExpanded()).toBe(true)
  })

  it('auto-expands when factory is blocked', () => {
    const dashboard = ref<FactoryDashboard | null>({
      ...baseDashboard,
      factory_status: { ...baseDashboard.factory_status, state: 'blocked' },
      repair: {
        blocked_count: 1,
        items: [
          {
            chapter_id: '008',
            title: '第 8 章',
            reason: '门禁未过',
            manual_hint: '先修稿',
            recommended_action: 'auto_repair',
          },
        ],
      },
    })
    const { showAdvanced } = useFactoryAdvancedView(dashboard)
    expect(showAdvanced.value).toBe(true)
  })

  it('shouldAutoExpandFactoryAdvanced respects repair count', () => {
    expect(
      shouldAutoExpandFactoryAdvanced({
        ...baseDashboard,
        factory_status: { ...baseDashboard.factory_status, state: 'ready' },
        repair: { blocked_count: 2, items: [] },
      }),
    ).toBe(true)
  })
})