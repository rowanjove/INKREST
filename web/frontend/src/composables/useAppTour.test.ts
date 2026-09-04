import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  APP_TOUR_STEPS,
  completeOnboarding,
  isAppTourPending,
  isOnboardingCompleted,
  markAppTourPending,
  markAppTourCompleted,
  shouldStartAppTour,
} from './useAppTour'

describe('useAppTour helpers', () => {
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

  it('tracks onboarding completion', () => {
    expect(isOnboardingCompleted()).toBe(false)
    completeOnboarding()
    expect(isOnboardingCompleted()).toBe(true)
  })

  it('exposes five tour steps', () => {
    expect(APP_TOUR_STEPS).toHaveLength(5)
  })

  it('only references current V2 routes and stable shell anchors', () => {
    expect(APP_TOUR_STEPS.map((step) => step.route)).toEqual([
      '/',
      '/workspace',
      '/workspace',
      '/workspace',
      '/workspace',
    ])
    expect(APP_TOUR_STEPS.map((step) => step.selector)).toEqual([
      '[data-tour="library-header"]',
      '[data-tour="nav-overview"]',
      '[data-tour="project-journey"]',
      '[data-tour="next-action"]',
      '[data-tour="command-palette"]',
    ])
    expect(APP_TOUR_STEPS.map((step) => `${step.title}${step.body}`).join(''))
      .not.toMatch(/AI 工厂|套路工坊|山山/)
  })

  it('stops auto tour after completion', () => {
    expect(shouldStartAppTour()).toBe(true)
    markAppTourCompleted()
    expect(shouldStartAppTour()).toBe(false)
  })

  it('tracks pending product tour marker', () => {
    expect(isAppTourPending()).toBe(false)
    markAppTourPending()
    expect(isAppTourPending()).toBe(true)
    markAppTourCompleted()
    expect(isAppTourPending()).toBe(false)
  })
})
