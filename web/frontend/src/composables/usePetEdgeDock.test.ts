import { describe, expect, it } from 'vitest'
import {
  analyzeEdgeProximity,
  dockedPosition,
  magneticSnapPosition,
  clampToWorkArea,
  PEEK_PX,
  EDGE_MARGIN_PX,
} from './usePetEdgeDock'

describe('usePetEdgeDock', () => {
  const workArea = { x: 0, y: 0, width: 1920, height: 1080 }
  const bounds = { x: 10, y: 100, width: 180, height: 180 }

  it('correctly analyzes edge proximity for left side', () => {
    const analysis = analyzeEdgeProximity(bounds, workArea)
    expect(analysis.edge).toBe('left')
    expect(analysis.distance).toBe(10)
    expect(analysis.isPushedOut).toBe(false)
  })

  it('detects when pushed out of bounds', () => {
    const pushedLeft = { x: -20, y: 100, width: 180, height: 180 }
    const analysis = analyzeEdgeProximity(pushedLeft, workArea)
    expect(analysis.edge).toBe('left')
    expect(analysis.isPushedOut).toBe(true)
  })

  it('correctly calculates docked position for left and right edges', () => {
    const leftDocked = dockedPosition('left', bounds, workArea)
    expect(leftDocked.x).toBe(workArea.x - bounds.width + PEEK_PX)
    expect(leftDocked.y).toBe(bounds.y)

    const rightDocked = dockedPosition('right', bounds, workArea)
    expect(rightDocked.x).toBe(workArea.x + workArea.width - PEEK_PX)
    expect(rightDocked.y).toBe(bounds.y)
  })

  it('correctly calculates magnetic snap position (inside screen with margin)', () => {
    const leftSnap = magneticSnapPosition('left', bounds, workArea)
    expect(leftSnap.x).toBe(workArea.x + EDGE_MARGIN_PX)
    expect(leftSnap.y).toBe(bounds.y)

    const rightSnap = magneticSnapPosition('right', bounds, workArea)
    expect(rightSnap.x).toBe(workArea.x + workArea.width - bounds.width - EDGE_MARGIN_PX)
    expect(rightSnap.y).toBe(bounds.y)
  })

  it('clamps positions properly to work area', () => {
    const outPos = { x: -100, y: 2000 }
    const clamped = clampToWorkArea(outPos, bounds, workArea)
    expect(clamped.x).toBe(workArea.x)
    expect(clamped.y).toBe(workArea.y + workArea.height - bounds.height)
  })
})
