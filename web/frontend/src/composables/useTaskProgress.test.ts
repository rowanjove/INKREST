import { describe, expect, it, vi } from 'vitest'
import { createRuntimeLogTransport, createTaskListTransport } from './useTaskProgress'

describe('useTaskProgress transports', () => {
  it('exposes task list transport lifecycle methods', () => {
    const transport = createTaskListTransport({ onTasksList: vi.fn() })
    expect(typeof transport.start).toBe('function')
    expect(typeof transport.stop).toBe('function')
    expect(typeof transport.refresh).toBe('function')
  })

  it('exposes runtime log transport lifecycle methods', () => {
    const transport = createRuntimeLogTransport({
      onRuntimeLog: vi.fn(),
      getLastLogId: () => 0,
      setLastLogId: vi.fn(),
    })
    expect(typeof transport.start).toBe('function')
    expect(typeof transport.stop).toBe('function')
  })
})