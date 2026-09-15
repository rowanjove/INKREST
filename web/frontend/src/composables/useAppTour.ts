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
    id: 'overview',
    title: '概览：先看清，再动手',
    body: '项目健康、正文进度、阻塞项与安全的下一步都汇总在这里。任何生产动作都会先进入确认页面。',
    route: '/workspace',
    selector: '[data-tour="nav-overview"]',
  },
  {
    id: 'journey',
    title: '六大核心创作中心',
    body: '自动生产按概览、策划、生产、正文、质量、发布推进；手写时也可以从策划直接进入正文。',
    route: '/workspace',
    selector: '[data-tour="project-journey"]',
  },
  {
    id: 'next-action',
    title: '跟着安全的下一步继续',
    body: '无论正在哪个页面，顶栏都会给出当前项目的首选下一步，减少来回寻找入口。',
    route: '/workspace',
    selector: '[data-tour="next-action"]',
  },
  {
    id: 'command-palette',
    title: '熟练后，用命令面板提速',
    body: '按 Ctrl K 搜索页面、章节、人物和下一步动作。各类中心与快捷操作始终可以从这里直达。',
    route: '/workspace',
    selector: '[data-tour="command-palette"]',
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
