import { onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { expandPendingPanel } from './usePendingPanelExpand'

export function useChapterMaintenance() {
  const route = useRoute()

  const maybeExpandAlerts = async () => {
    if (route.query.expand === 'alerts') {
      await expandPendingPanel(true)
    }
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