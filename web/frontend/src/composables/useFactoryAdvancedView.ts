import { ref, watch, type Ref } from 'vue'
import type { FactoryDashboard } from '../types/factory'

const STORAGE_KEY = 'inkrest.factory.advancedExpanded'

export function shouldAutoExpandFactoryAdvanced(
  dashboard: FactoryDashboard | null | undefined,
): boolean {
  if (!dashboard) return false
  if (dashboard.factory_status.state === 'blocked') return true
  if ((dashboard.repair?.blocked_count || 0) > 0) return true
  return false
}

export function readFactoryAdvancedExpanded(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

export function writeFactoryAdvancedExpanded(expanded: boolean): void {
  try {
    localStorage.setItem(STORAGE_KEY, expanded ? '1' : '0')
  } catch {
    /* ignore quota / private mode */
  }
}

export function useFactoryAdvancedView(
  dashboard: Ref<FactoryDashboard | null | undefined>,
) {
  const showAdvanced = ref(readFactoryAdvancedExpanded())

  watch(
    dashboard,
    (value) => {
      if (shouldAutoExpandFactoryAdvanced(value)) {
        showAdvanced.value = true
      }
    },
    { immediate: true },
  )

  function toggleFactoryAdvanced() {
    showAdvanced.value = !showAdvanced.value
    writeFactoryAdvancedExpanded(showAdvanced.value)
  }

  function expandFactoryAdvanced() {
    showAdvanced.value = true
    writeFactoryAdvancedExpanded(true)
  }

  return {
    showAdvanced,
    toggleFactoryAdvanced,
    expandFactoryAdvanced,
  }
}