<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import PendingChaptersPanel from '../components/PendingChaptersPanel.vue'
import SemiAutoRepairHint from '../components/SemiAutoRepairHint.vue'
import BatchRunStatusBanner from '../components/BatchRunStatusBanner.vue'
import NovelBatchRunDialog from '../components/NovelBatchRunDialog.vue'
import { useChapterMaintenance } from '../composables/useChapterMaintenance'
import { useTasksStore } from '../stores/tasks'

useChapterMaintenance()

const tasksStore = useTasksStore()

onMounted(() => {
  tasksStore.connectElectronEvents()
  tasksStore.startPolling()
  tasksStore.startRuntimeLogPolling()
})

onUnmounted(() => {
  tasksStore.stopPolling()
  tasksStore.stopRuntimeLogPolling()
})
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