import { onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { expandPendingPanel } from './usePendingPanelExpand'

export function useChapterMaintenance() {
  const route = useRoute()
  let lastExpandedQuery = ''

  const maybeExpandAlerts = async () => {
    const expand = route.query.expand
    if (expand !== 'alerts') {
      lastExpandedQuery = ''
      return
    }
    const key = String(expand)
    if (lastExpandedQuery === key) return
    lastExpandedQuery = key
    await expandPendingPanel(true)
  }

  onMounted(() => {
    void maybeExpandAlerts()
  })

  watch(
    () => route.query.expand,
    () => {
      void maybeExpandAlerts()
    },
  )
}