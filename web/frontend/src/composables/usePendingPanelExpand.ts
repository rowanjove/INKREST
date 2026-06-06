import { nextTick, ref } from 'vue'

export const pendingPanelExpanded = ref(false)

export async function expandPendingPanel(scroll = true) {
  pendingPanelExpanded.value = true
  if (!scroll) return
  await nextTick()
  document.getElementById('pipeline-alerts-section')?.scrollIntoView({
    behavior: 'smooth',
    block: 'start',
  })
}