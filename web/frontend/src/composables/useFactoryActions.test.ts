import { describe, expect, it, vi } from 'vitest'
import { resolveFactoryIntent, resolveFactoryRiskAction } from './useFactoryActions'
import type { FactoryRiskAction } from '../types/factory'

describe('useFactoryActions', () => {
  it('routes create and plan to /create', () => {
    const navigate = vi.fn()
    resolveFactoryIntent('create', { navigate })
    resolveFactoryIntent('plan', { navigate })
    expect(navigate).toHaveBeenCalledWith('/create')
  })

  it('routes repair to maintenance alerts', () => {
    const navigate = vi.fn()
    resolveFactoryIntent('repair', { navigate })
    expect(navigate).toHaveBeenCalledWith('/chapters/maintenance?expand=alerts')
  })

  it('prefers onExport callback for export intent', () => {
    const navigate = vi.fn()
    const onExport = vi.fn()
    resolveFactoryIntent('export', { navigate, onExport })
    expect(onExport).toHaveBeenCalledOnce()
    expect(navigate).not.toHaveBeenCalled()
  })

  it('prefers onRun callback for run intent', () => {
    const navigate = vi.fn()
    const onRun = vi.fn()
    resolveFactoryIntent('run', { navigate, onRun })
    expect(onRun).toHaveBeenCalledOnce()
    expect(navigate).not.toHaveBeenCalled()
  })

  it('falls back to pipeline focus when run has no callback', () => {
    const navigate = vi.fn()
    resolveFactoryIntent('run', { navigate })
    expect(navigate).toHaveBeenCalledWith('/workspace?focus=pipeline')
  })

  it('routes risk chapter actions to chapter detail', () => {
    const navigate = vi.fn()
    const action: FactoryRiskAction = {
      id: 'chapter',
      label: 'Open chapter',
      intent: 'chapter',
      route: '/chapters/008',
      reason: 'Quality issue',
    }
    resolveFactoryRiskAction(action, { navigate })
    expect(navigate).toHaveBeenCalledWith('/chapters/008')
  })
})