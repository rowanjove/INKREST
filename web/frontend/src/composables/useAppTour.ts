import { computed, ref } from 'vue'
import type { Router } from 'vue-router'

const ONBOARDING_KEY = 'inkrest.onboarding.completed'
const TOUR_DONE_KEY = 'inkrest.app_tour.completed'
const TOUR_PENDING_KEY = 'inkrest.app_tour.pending'
const TOUR_STEP_KEY = 'inkrest.app_tour.step'

export type AppTourStep = {
  id: string
  title: string
  body: string
  route: string
  selector: string
}

export const APP_TOUR_STEPS: AppTourStep[] = [
  {
    id: 'library',
    title: '书库：一切从这里开始',
    body: '新建、导入或打开作品。没头绪时，先点「导入示例书」——约 1 分钟跑通工厂全流程。',
    route: '/',
    selector: '[data-tour="library-header"]',
  },
  {
    id: 'factory',
    title: 'AI 工厂控制台',
    body: '看生产计划、章节进度与风险雷达；阻断章节可在此自动修复，修完一键回到连写区。',
    route: '/workspace',
    selector: '[data-tour="factory-control"]',
  },
  {
    id: 'trope',
    title: '套路工坊：快速开书',
    body: '拖拽组合频道、题材与爽点，点「用此模板开书」——创建页自动预填，三步到可生产。',
    route: '/trope-workshop',
    selector: '[data-tour="trope-workbench"]',
  },
  {
    id: 'pet',
    title: '山山：写书时的工厂管家',
    body: '打开桌宠气泡，不用切回工作台——看简报、点修复、跳连写，日常排障 ≤2 次点击。',
    route: '/workspace',
    selector: '[data-tour="engine-pill"]',
  },
  {
    id: 'config',
    title: '设置：配好模型就能写',
    body: '日常 LLM 配通即可开书；向量嵌入可后补，不挡首本体验。发版前建议在此测连通性。',
    route: '/config',
    selector: '[data-tour="config-nav"]',
  },
]

export function isOnboardingCompleted(): boolean {
  try {
    return localStorage.getItem(ONBOARDING_KEY) === '1'
  } catch {
    return false
  }
}

export function completeOnboarding() {
  try {
    localStorage.setItem(ONBOARDING_KEY, '1')
  } catch {
    /* ignore */
  }
}

export function isAppTourPending(): boolean {
  try {
    return localStorage.getItem(TOUR_PENDING_KEY) === '1'
  } catch {
    return false
  }
}

export function markAppTourPending() {
  try {
    localStorage.setItem(TOUR_PENDING_KEY, '1')
  } catch {
    /* ignore */
  }
}

export function shouldStartAppTour(): boolean {
  try {
    if (localStorage.getItem(TOUR_DONE_KEY) === '1') return false
    return localStorage.getItem(TOUR_PENDING_KEY) === '1' || !localStorage.getItem(TOUR_DONE_KEY)
  } catch {
    return true
  }
}

export function markAppTourCompleted() {
  try {
    localStorage.setItem(TOUR_DONE_KEY, '1')
    localStorage.removeItem(TOUR_PENDING_KEY)
    localStorage.removeItem(TOUR_STEP_KEY)
  } catch {
    /* ignore */
  }
}

export function useAppTour(router: Router) {
  const active = ref(false)
  const stepIndex = ref(0)

  const currentStep = computed(() => APP_TOUR_STEPS[stepIndex.value] || null)

  function readSavedStep() {
    try {
      const raw = Number(localStorage.getItem(TOUR_STEP_KEY) || '0')
      if (Number.isFinite(raw) && raw >= 0 && raw < APP_TOUR_STEPS.length) {
        stepIndex.value = raw
      }
    } catch {
      stepIndex.value = 0
    }
  }

  function persistStep() {
    try {
      localStorage.setItem(TOUR_STEP_KEY, String(stepIndex.value))
    } catch {
      /* ignore */
    }
  }

  async function openTour(startAt = 0) {
    stepIndex.value = Math.max(0, Math.min(startAt, APP_TOUR_STEPS.length - 1))
    active.value = true
    persistStep()
    await navigateToCurrentStep()
  }

  async function navigateToCurrentStep() {
    const step = currentStep.value
    if (!step) return
    if (router.currentRoute.value.path !== step.route) {
      await router.push(step.route)
    }
    await new Promise((resolve) => window.setTimeout(resolve, 120))
  }

  async function nextStep() {
    if (stepIndex.value >= APP_TOUR_STEPS.length - 1) {
      finishTour()
      return
    }
    stepIndex.value += 1
    persistStep()
    await navigateToCurrentStep()
  }

  function prevStep() {
    if (stepIndex.value <= 0) return
    stepIndex.value -= 1
    persistStep()
    void navigateToCurrentStep()
  }

  function finishTour() {
    active.value = false
    markAppTourCompleted()
  }

  function skipTour() {
    finishTour()
  }

  async function maybeAutoStart() {
    if (!shouldStartAppTour()) return
    readSavedStep()
    await openTour(stepIndex.value)
  }

  return {
    active,
    stepIndex,
    currentStep,
    totalSteps: APP_TOUR_STEPS.length,
    openTour,
    nextStep,
    prevStep,
    skipTour,
    maybeAutoStart,
  }
}
