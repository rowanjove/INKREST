import { EventEmitter } from 'node:events'
import { PassThrough } from 'node:stream'
import type { ChildProcess, spawn } from 'node:child_process'
import { describe, expect, it, vi } from 'vitest'

import { PythonBridge } from './python-bridge'

class FakeChild extends EventEmitter {
  stdout = new PassThrough()
  stderr = new PassThrough()
  killed = false
  exitCode: number | null = null
  readonly signals: Array<NodeJS.Signals | number | undefined> = []

  kill(signal?: NodeJS.Signals | number): boolean {
    this.signals.push(signal)
    if (this.exitCode !== null) return false
    this.killed = true
    queueMicrotask(() => {
      this.exitCode = 0
      this.emit('exit', 0, signal)
    })
    return true
  }
}

function createBridge(children: FakeChild[]) {
  const spawnProcess = vi.fn(() => {
    const child = children.shift()
    if (!child) throw new Error('unexpected spawn')
    return child as unknown as ChildProcess
  }) as unknown as typeof spawn
  const fetchHealth = vi.fn(async () => ({ ok: true })) as unknown as typeof fetch
  const bridge = new PythonBridge(process.cwd(), {
    spawnProcess,
    fetchHealth,
    pythonCommand: 'python',
  })
  return { bridge, spawnProcess, fetchHealth }
}

describe('PythonBridge server lifecycle', () => {
  it('coalesces concurrent starts and waits for the same health result', async () => {
    const child = new FakeChild()
    const { bridge, spawnProcess, fetchHealth } = createBridge([child])

    await Promise.all([bridge.startServer(8123), bridge.startServer(8123)])

    expect(spawnProcess).toHaveBeenCalledTimes(1)
    expect(fetchHealth).toHaveBeenCalledTimes(1)
    expect(bridge.isServerRunning()).toBe(true)
    await bridge.stopServer()
  })

  it('rejects a second port while the server is running', async () => {
    const child = new FakeChild()
    const { bridge } = createBridge([child])
    await bridge.startServer(8123)

    await expect(bridge.startServer(8124)).rejects.toThrow(
      'already running on port 8123',
    )
    await bridge.stopServer()
  })

  it('coalesces concurrent stops and permits one clean restart', async () => {
    const first = new FakeChild()
    const second = new FakeChild()
    const { bridge, spawnProcess } = createBridge([first, second])
    await bridge.startServer(8123)

    await Promise.all([bridge.stopServer(), bridge.stopServer()])

    expect(first.signals).toEqual(['SIGTERM'])
    expect(bridge.isServerRunning()).toBe(false)
    await bridge.startServer(8123)
    expect(spawnProcess).toHaveBeenCalledTimes(2)
    expect(bridge.isServerRunning()).toBe(true)
    await bridge.stopServer()
  })
})
