<script setup lang="ts">
import { useRouter } from 'vue-router'
import { Refresh } from '@element-plus/icons-vue'
import StateSettingsTab from '../components/state/StateSettingsTab.vue'
import StateChronicleTab from '../components/state/StateChronicleTab.vue'
import PlanningSectionNav from '../components/planning/PlanningSectionNav.vue'
import PlanningWorkspaceHeader from '../components/planning/PlanningWorkspaceHeader.vue'
import { useStateViewSettings } from '../composables/useStateViewSettings'
import { useStateViewChronicle } from '../composables/useStateViewChronicle'

const router = useRouter()

const {
  state,
  eventQuery,
  loadError,
  activeTab,
  charPage,
  forePage,
  hookPage,
  objPage,
  eventPage,
  pageSize,
  chapterRange,
  maxChapter,
  sliderMarks,
  loadState,
  handleCollect,
  handleSearch,
  filteredCharacters,
  filteredForeshadows,
  filteredHooks,
  filteredObjects,
  filteredEvents,
  paginatedCharacters,
  paginatedForeshadows,
  paginatedHooks,
  paginatedObjects,
  paginatedEvents,
} = useStateViewSettings()

const {
  activeOuterTab,
  activeTimelineTab,
  chronicleRefreshing,
  timelinePageSize,
  timelineEventPage,
  timelineFsPage,
  timelineHookPage,
  timelineNodePage,
  timelineEvents,
  timelineForeshadows,
  timelineHooks,
  timelineNodes,
  chapterGoalPreviews,
  showChapterGoalPreview,
  chronicleStats,
  refreshChronicle,
  paginatedTimelineEvents,
  paginatedTimelineForeshadows,
  paginatedTimelineHooks,
  paginatedTimelineNodes,
  characters,
  graphViewport,
  graphNodes,
  graphEdges,
  graphHasRenderableNodes,
  hoveredEdge,
  edgeTooltipStyle,
  showEdgeTooltip,
  hideEdgeTooltip,
  truncateGraphName,
  dialogVisible,
  dialogMode,
  relationForm,
  openAddRelation,
  openEditRelation,
  submitRelation,
  deleteRelation,
} = useStateViewChronicle({ state, chapterRange, loadState })

const goChapters = () => router.push('/chapters')
const goMonitor = () => router.push('/production?tab=runs')
const goSettingsTab = () => {
  activeOuterTab.value = 'settings'
}
</script>

<template>
  <section class="planning-page state-page">
    <PlanningWorkspaceHeader
      eyebrow="策划中心"
      title="剧情状态"
      description="追踪人物变化、伏笔债务、道具线索与时空编年，对照设定与正文的实际进展。"
    >
      <template #actions>
        <el-button type="primary" :icon="Refresh" :loading="chronicleRefreshing" @click="refreshChronicle(false)">
          刷新状态
        </el-button>
      </template>
    </PlanningWorkspaceHeader>

    <PlanningSectionNav />

    <div class="state-content">
      <el-alert v-if="loadError" :title="loadError" type="warning" show-icon class="state-load-error" />
      <template v-if="state">
        <nav class="state-mode-bar" aria-label="剧情状态视图">
          <el-segmented
            v-model="activeOuterTab"
            :options="[
              { label: '剧情设定库', value: 'settings' },
              { label: '时空编年史', value: 'chronicle' },
            ]"
          />
          <span>设定是基准，编年史记录正文已发生的变化</span>
        </nav>

        <div class="state-workspace">
          <StateSettingsTab
            v-if="activeOuterTab === 'settings'"
            v-model:chapter-range="chapterRange"
            v-model:active-tab="activeTab"
            v-model:char-page="charPage"
            v-model:fore-page="forePage"
            v-model:hook-page="hookPage"
            v-model:obj-page="objPage"
            v-model:event-page="eventPage"
            v-model:event-query="eventQuery"
            :max-chapter="maxChapter"
            :slider-marks="sliderMarks"
            :page-size="pageSize"
            :paginated-characters="paginatedCharacters"
            :filtered-characters-total="filteredCharacters.length"
            :paginated-foreshadows="paginatedForeshadows"
            :filtered-foreshadows-total="filteredForeshadows.length"
            :paginated-hooks="paginatedHooks"
            :filtered-hooks-total="filteredHooks.length"
            :paginated-objects="paginatedObjects"
            :filtered-objects-total="filteredObjects.length"
            :paginated-events="paginatedEvents"
            :filtered-events-total="filteredEvents.length"
            :on-collect="handleCollect"
            :on-search="handleSearch"
            :on-load-state="loadState"
          />

          <StateChronicleTab
            v-else
            v-model:chapter-range="chapterRange"
            v-model:active-timeline-tab="activeTimelineTab"
            v-model:timeline-event-page="timelineEventPage"
            v-model:timeline-fs-page="timelineFsPage"
            v-model:timeline-hook-page="timelineHookPage"
            v-model:timeline-node-page="timelineNodePage"
            v-model:dialog-visible="dialogVisible"
            :max-chapter="maxChapter"
            :chronicle-refreshing="chronicleRefreshing"
            :chronicle-stats="chronicleStats"
            :timeline-page-size="timelinePageSize"
            :timeline-events="timelineEvents"
            :timeline-foreshadows="timelineForeshadows"
            :timeline-hooks="timelineHooks"
            :timeline-nodes="timelineNodes"
            :chapter-goal-previews="chapterGoalPreviews"
            :show-chapter-goal-preview="showChapterGoalPreview"
            :paginated-timeline-events="paginatedTimelineEvents"
            :paginated-timeline-foreshadows="paginatedTimelineForeshadows"
            :paginated-timeline-hooks="paginatedTimelineHooks"
            :paginated-timeline-nodes="paginatedTimelineNodes"
            :graph-viewport="graphViewport"
            :graph-nodes="graphNodes"
            :graph-edges="graphEdges"
            :graph-has-renderable-nodes="graphHasRenderableNodes"
            :hovered-edge="hoveredEdge"
            :edge-tooltip-style="edgeTooltipStyle"
            :characters="characters"
            :dialog-mode="dialogMode"
            :relation-form="relationForm"
            :truncate-graph-name="truncateGraphName"
            :on-refresh-chronicle="() => refreshChronicle()"
            :on-go-chapters="goChapters"
            :on-go-monitor="goMonitor"
            :on-go-settings-tab="goSettingsTab"
            :on-open-add-relation="openAddRelation"
            :on-open-edit-relation="openEditRelation"
            :on-show-edge-tooltip="showEdgeTooltip"
            :on-hide-edge-tooltip="hideEdgeTooltip"
            :on-delete-relation="deleteRelation"
            :on-submit-relation="submitRelation"
          />
        </div>
      </template>
      <el-skeleton v-else :rows="10" animated class="state-skeleton" />
    </div>
  </section>
</template>

<style scoped>
.state-page {
  min-width: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--color-bg-canvas);
}
.state-content { flex: 1; min-height: 0; overflow: auto; background: var(--color-bg-page); }
.state-load-error { border-radius: 0; }
.state-mode-bar {
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: 7px var(--space-5);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-surface);
}
.state-mode-bar span { color: var(--color-text-muted); font-size: 11px; }
.state-workspace,
.state-skeleton { padding: var(--space-5); }

@media (max-width: 720px) {
  .state-mode-bar { align-items: flex-start; flex-direction: column; }
  .state-workspace,
  .state-skeleton { padding: var(--space-3); }
}
</style>
