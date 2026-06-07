<script setup lang="ts">
import DashboardStats from '../DashboardStats.vue'
import ProjectReadinessCard from '../workbench/ProjectReadinessCard.vue'
import AgentProductionLine from '../workbench/AgentProductionLine.vue'
import ScaleArchitecturePanel from '../workbench/ScaleArchitecturePanel.vue'

defineProps<{
  engineStatus: { ready: boolean; label: string; route: string }
  outline: Record<string, any> | null
  assets: any[]
  maxAvailableChapters: number
  semanticSearchEffective: boolean
  vectorEnabledForProject: boolean
  workScale: string
  scaleProfile: Record<string, any>
  chapterCountTotal: number
}>()

const emit = defineEmits<{
  saved: []
}>()
</script>

<template>
  <div class="workbench-pane">
    <DashboardStats class="workbench-stats workbench-stats-top" />

    <ProjectReadinessCard
      :engine-ready="engineStatus.ready"
      :outline="outline"
      :assets="assets"
      :max-available-chapters="maxAvailableChapters"
      :semantic-search-effective="semanticSearchEffective"
      :vector-enabled="vectorEnabledForProject"
      :work-scale="workScale"
    />

    <AgentProductionLine
      :engine-ready="engineStatus.ready"
      :outline="outline"
      :assets="assets"
      :max-available-chapters="maxAvailableChapters"
      :semantic-search-effective="semanticSearchEffective"
      :vector-enabled="vectorEnabledForProject"
      :work-scale="workScale"
      show-controls
    />

    <ScaleArchitecturePanel
      :outline="outline"
      :scale-profile="scaleProfile"
      :chapters-written="chapterCountTotal"
      @saved="emit('saved')"
    />
  </div>
</template>

<style scoped>
.workbench-pane {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: min-content;
  padding-bottom: 8px;
}

.workbench-stats {
  flex-shrink: 0;
}

.workbench-stats-top {
  margin-bottom: 16px;
}

.workbench-stats :deep(.metric-grid) {
  gap: 10px;
}

.workbench-stats :deep(.metric) {
  min-height: 68px;
  padding: 10px 12px;
}

.workbench-stats :deep(.metric-icon) {
  width: 40px;
  height: 40px;
  font-size: 18px;
}

.workbench-stats :deep(.metric-value) {
  font-size: 22px;
  margin-top: 4px;
}

.workbench-stats :deep(.metric-label) {
  font-size: 12px;
}

.workbench-pane > :deep(.readiness-row),
.workbench-pane > :deep(.production-line) {
  margin-bottom: 16px;
}
</style>