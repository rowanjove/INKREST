<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Pane, Splitpanes } from 'splitpanes'
import 'splitpanes/dist/splitpanes.css'
import { Refresh } from '@element-plus/icons-vue'
import PlanningEntityTree from '../components/planning/PlanningEntityTree.vue'
import PlanningCanvas from '../components/planning/PlanningCanvas.vue'
import PlanningInspector from '../components/planning/PlanningInspector.vue'
import PlanningSectionNav from '../components/planning/PlanningSectionNav.vue'
import PlanningWorkspaceHeader from '../components/planning/PlanningWorkspaceHeader.vue'
import OutlineMindmapPane from '../components/outline/OutlineMindmapPane.vue'
import ErrorState from '../shared/ui/ErrorState.vue'
import StatusBadge from '../shared/ui/StatusBadge.vue'
import { PLANNING_KIND_LABELS } from '../entities/planning/planningWorkspace'
import { usePlanningWorkspace } from '../composables/usePlanningWorkspace'
import { useOutlineView } from '../composables/useOutlineView'

const OutlineEditor = defineAsyncComponent(() => import('./OutlineEditor.vue'))
const route = useRoute()
const router = useRouter()
type PlanningViewMode = 'editor' | 'mindmap' | 'cards' | 'relations' | 'timeline'
const planningViewFromQuery = (): PlanningViewMode => {
  const value = String(route.query.view || '')
  return ['mindmap', 'cards', 'relations', 'timeline'].includes(value)
    ? value as PlanningViewMode
    : 'editor'
}
const viewMode = ref<PlanningViewMode>('editor')
const advanced = ref(false)
const showWelcome = ref(false)
const pageTitle = computed(() => (viewMode.value === 'editor' ? '大纲编辑' : '故事图谱'))
const pageDescription = computed(() => (
  viewMode.value === 'editor'
    ? '设定小说大纲、题材定位、爽点机制与篇章规划。'
    : '可视化查看故事实体、人物关系网络与关键事件时间线。'
))
const {
  workspace,
  loading,
  error,
  selectedId,
  selectedEntity,
  query,
  filteredEntities,
  selectEntity,
  load,
} = usePlanningWorkspace()

const {
  title: outlineTitle,
  genre: outlineGenre,
  targetChapters: outlineTargetChapters,
  arcs: outlineArcs,
  connections: mindmapConnections,
  setNodeRef: setMindmapNodeRef,
  displayIndex,
  load: loadOutline,
} = useOutlineView()

function selectById(id: string) {
  const entity = workspace.value.entities.find((item) => item.id === id)
  if (entity) selectEntity(entity)
}

function selectArcEntity(arc: any, idx: number) {
  const arcTitle = typeof arc === 'string' ? arc : (arc?.title || arc?.name || `阶段 ${displayIndex(idx)}`)
  const found = workspace.value.entities.find((item) =>
    item.kind === 'outline' && (item.name === arcTitle || item.name.includes(arcTitle) || arcTitle.includes(item.name))
  )
  if (found) {
    selectEntity(found)
  }
}

async function handleRefresh() {
  await Promise.all([load(), loadOutline()])
}

watch(
  () => route.query.view,
  () => { viewMode.value = planningViewFromQuery() },
  { immediate: true },
)

watch(viewMode, (value) => {
  const current = planningViewFromQuery()
  if (value === current) return
  const query = { ...route.query }
  if (value === 'editor') delete query.view
  else query.view = value
  void router.replace({ path: '/outline', query })
})

onMounted(() => {
  if (String(route.query.welcome || '') !== '1') return
  showWelcome.value = true
  const nextQuery = { ...route.query }
  delete nextQuery.welcome
  void router.replace({ path: route.path, query: nextQuery })
})
</script>

<template>
  <section class="planning-page" v-loading="loading">
    <PlanningWorkspaceHeader
      eyebrow="策划中心"
      :title="pageTitle"
      :description="pageDescription"
    >
      <template #meta>
        <div class="count-badges">
          <StatusBadge
            v-for="(count, kind) in workspace.counts"
            :key="kind"
            :label="`${PLANNING_KIND_LABELS[kind] || kind} ${count}`"
          />
        </div>
      </template>
      <template #actions>
        <el-switch v-model="advanced" inline-prompt active-text="高级" inactive-text="简洁" />
        <el-button :icon="Refresh" circle aria-label="刷新策划数据" @click="handleRefresh" />
      </template>
    </PlanningWorkspaceHeader>

    <PlanningSectionNav />

    <el-alert
      v-if="showWelcome"
      class="planning-warning"
      type="success"
      show-icon
      closable
      title="作品骨架已建好"
      description="先补全人物、世界和卷弧。生产动作仍要到生产中心确认，这里不会自动生成章节。"
      @close="showWelcome = false"
    />
    <el-alert
      v-for="warning in workspace.warnings"
      :key="warning"
      :title="warning"
      type="warning"
      :closable="false"
      show-icon
      class="planning-warning"
    />

    <ErrorState
      v-if="error"
      title="策划数据暂时无法加载"
      :description="error"
      action-label="重试"
      @action="handleRefresh"
    />

    <template v-else>
      <nav v-if="viewMode !== 'editor'" class="canvas-tabs" aria-label="故事图谱视图">
        <el-segmented
          v-model="viewMode"
          :options="[
            { label: '思维导图', value: 'mindmap' },
            { label: '卡片大纲', value: 'cards' },
            { label: '关系图', value: 'relations' },
            { label: '时间线', value: 'timeline' },
          ]"
        />
        <span v-if="advanced" class="advanced-note">高级模式显示数据来源和原始字段</span>
      </nav>

      <div v-if="viewMode === 'editor'" class="legacy-editor">
        <OutlineEditor :advanced="advanced" />
      </div>

      <Splitpanes v-else class="planning-split" :dbl-click-splitter="false">
        <Pane :size="22" :min-size="16" :max-size="34">
          <PlanningEntityTree
            v-model:query="query"
            :entities="filteredEntities"
            :selected-id="selectedId"
            @select="selectEntity"
          />
        </Pane>
        <Pane :size="55" :min-size="35">
          <OutlineMindmapPane
            v-if="viewMode === 'mindmap'"
            :title="outlineTitle"
            :genre="outlineGenre"
            :target-chapters="outlineTargetChapters"
            :arcs="outlineArcs"
            :connections="mindmapConnections"
            :set-node-ref="setMindmapNodeRef"
            :display-index="displayIndex"
            @select="selectArcEntity"
          />
          <PlanningCanvas
            v-else
            :mode="viewMode as 'cards' | 'relations' | 'timeline'"
            :entities="workspace.entities"
            :relations="workspace.relations"
            :timeline="workspace.timeline"
            @select="selectById"
          />
        </Pane>
        <Pane :size="23" :min-size="18" :max-size="36">
          <PlanningInspector :entity="selectedEntity" />
          <p v-if="advanced && selectedEntity" class="source-path">
            数据来源：{{ selectedEntity.source }}
          </p>
        </Pane>
      </Splitpanes>
    </template>
  </section>
</template>

<style scoped>
.planning-page {
  min-width: 0;
  height: 100%;
  overflow-y: auto;
  scrollbar-gutter: stable;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-canvas);
}

.count-badges { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 5px; }
.planning-warning { border-radius: 0; }

.canvas-tabs {
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: 7px var(--space-5);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-surface);
}
.advanced-note { color: var(--color-text-muted); font-size: 11px; }
.planning-split { flex: 1; min-height: 580px; }
.legacy-editor { flex: 1; padding: var(--space-5); background: var(--color-bg-page); }
.source-path { margin: -10px var(--space-4) var(--space-4); color: var(--color-text-muted); font-size: 11px; word-break: break-all; }

:deep(.splitpanes__splitter) {
  position: relative;
  width: 5px;
  background: var(--color-border-subtle);
}
:deep(.splitpanes__splitter::before) {
  content: '';
  position: absolute;
  inset: 0 -3px;
}
:deep(.splitpanes__pane) { overflow: hidden; }

@media (max-width: 900px) {
  .count-badges { justify-content: flex-start; }
  .planning-split { display: grid; grid-template-rows: auto minmax(460px, 1fr) auto; }
  :deep(.splitpanes__pane) { width: 100% !important; height: auto; }
  :deep(.splitpanes__splitter) { display: none; }
}
</style>
