<script setup lang="ts">
import {
  computed,
  defineAsyncComponent,
  onMounted,
  provide,
  ref,
  watch,
} from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppShell from './app/shell/AppShell.vue'
import { useDesktopLifecycle } from './app/bootstrap/useDesktopLifecycle'
import SetupWizard from './components/SetupWizard.vue'
import FirstBookGuide from './components/workbench/FirstBookGuide.vue'
import {
  isAppTourPending,
  isOnboardingCompleted,
  useAppTour,
} from './composables/useAppTour'
import { useProjectStore } from './stores/project'

const AppTourOverlay = defineAsyncComponent(
  () => import('./components/AppTourOverlay.vue'),
)
const NovelBatchRunDialog = defineAsyncComponent(
  () => import('./components/NovelBatchRunDialog.vue'),
)

const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()
const showSetupWizard = ref(false)
const isPetRoute = computed(
  () =>
    route.meta.scope === 'pet' ||
    route.path === '/pet' ||
    route.path === '/pet-bubble',
)

const {
  active: tourActive,
  stepIndex: tourStepIndex,
  currentStep: tourStep,
  totalSteps: tourTotalSteps,
  nextStep: tourNextStep,
  prevStep: tourPrevStep,
  skipTour,
  maybeAutoStart,
  openTour,
} = useAppTour(router)

const { backendStatus, backendUnreachable } = useDesktopLifecycle(
  router,
  isPetRoute,
)

provide('openSetupWizard', () => {
  showSetupWizard.value = true
})
provide('openAppTour', () => {
  void openTour(0)
})

const handleWizardCompleted = () => {
  showSetupWizard.value = false
  localStorage.setItem('setup_wizard_completed', 'true')
}

onMounted(async () => {
  if (isPetRoute.value) return
  await projectStore.hydrate()
  if (
    !isOnboardingCompleted() &&
    projectStore.projects.length === 0 &&
    route.path !== '/onboarding'
  ) {
    await router.push('/onboarding')
    return
  }
  if (isOnboardingCompleted()) void maybeAutoStart()
})

watch(
  () => route.path,
  () => {
    if (
      isOnboardingCompleted() &&
      isAppTourPending() &&
      !isPetRoute.value
    ) {
      void maybeAutoStart()
    }
  },
)
</script>

<template>
  <router-view v-if="isPetRoute" />
  <template v-else>
    <AppShell
      v-loading="backendStatus === 'restarting'"
      element-loading-text="后台服务异常中断，正在自动重启中，请稍候…"
      :backend-status="backendStatus"
      :backend-unreachable="backendUnreachable"
    />

    <SetupWizard
      :visible="showSetupWizard"
      @close="showSetupWizard = false"
      @completed="handleWizardCompleted"
    />

    <AppTourOverlay
      :visible="tourActive"
      :step="tourStep"
      :step-index="tourStepIndex"
      :total-steps="tourTotalSteps"
      @next="tourNextStep"
      @prev="tourPrevStep"
      @skip="skipTour"
    />

    <FirstBookGuide
      v-if="projectStore.currentProject?.id"
      :project-id="projectStore.currentProject.id"
    />

    <NovelBatchRunDialog />
  </template>
</template>
