<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import PendingChaptersPanel from '../components/PendingChaptersPanel.vue'
import SemiAutoRepairHint from '../components/SemiAutoRepairHint.vue'
import BatchRunStatusBanner from '../components/BatchRunStatusBanner.vue'
import NovelBatchRunDialog from '../components/NovelBatchRunDialog.vue'
import { expandPendingPanel } from '../composables/usePendingPanelExpand'

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
</script>

<template>
  <div class="chapter-maintenance-page">
    <BatchRunStatusBanner />
    <NovelBatchRunDialog />
    <SemiAutoRepairHint compact />
    <PendingChaptersPanel :show-actions="true" :hide-footnote="true" :link-focus="true" />
  </div>
</template>

<style scoped>
.chapter-maintenance-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chapter-maintenance-page > * {
  flex-shrink: 0;
}
</style>