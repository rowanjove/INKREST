<script setup lang="ts">
import { useRouter } from 'vue-router'
import { Refresh } from '@element-plus/icons-vue'
import StateSettingsTab from '../components/state/StateSettingsTab.vue'
import StateChronicleTab from '../components/state/StateChronicleTab.vue'
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
  <el-alert v-if="loadError" :title="loadError" type="warning" show-icon style="margin-bottom: 16px" />
  <div v-if="state">
    <header class="page-head">
      <div class="page-title-area">
        <h1>状态库</h1>
        <p>追踪小说角色属性、伏笔债务、物品状态以及时空编年史的发展脉络。</p>
      </div>
      <div class="page-actions">
        <el-button type="primary" :icon="Refresh" :loading="chronicleRefreshing" @click="refreshChronicle(false)">
          刷新载入
        </el-button>
      </div>
    </header>

    <el-tabs v-model="activeOuterTab" type="card" class="outer-state-tabs" style="margin-bottom: 20px;">
      <el-tab-pane label="📚 剧情设定库" name="settings">
        <StateSettingsTab
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
      </el-tab-pane>

      <el-tab-pane label="🌌 时空编年史" name="chronicle">
        <StateChronicleTab
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
      </el-tab-pane>
    </el-tabs>
  </div>
  <el-skeleton v-else :rows="10" animated />
</template>

<style scoped>
.outer-state-tabs {
  background: transparent;
}
</style>
