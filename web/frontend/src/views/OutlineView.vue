<script setup lang="ts">
import { defineAsyncComponent, ref } from 'vue'
import { Pane, Splitpanes } from 'splitpanes'
import 'splitpanes/dist/splitpanes.css'
import { Refresh } from '@element-plus/icons-vue'
import PlanningEntityTree from '../components/planning/PlanningEntityTree.vue'
import PlanningCanvas from '../components/planning/PlanningCanvas.vue'
import PlanningInspector from '../components/planning/PlanningInspector.vue'
import ErrorState from '../shared/ui/ErrorState.vue'
import StatusBadge from '../shared/ui/StatusBadge.vue'
import { PLANNING_KIND_LABELS } from '../entities/planning/planningWorkspace'
import { usePlanningWorkspace } from '../composables/usePlanningWorkspace'

const OutlineEditorLegacy = defineAsyncComponent(() => import('./OutlineEditorLegacy.vue'))
const viewMode = ref<'editor' | 'cards' | 'relations' | 'timeline'>('cards')
const advanced = ref(false)
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

function selectById(id: string) {
  const entity = workspace.value.entities.find((item) => item.id === id)
  if (entity) selectEntity(entity)
}
</script>

<template>
  <section class="planning-page" v-loading="loading">
    <header class="planning-header">
      <div>
        <p class="eyebrow">策划中心</p>
        <h1>故事世界工作台</h1>
        <p>在同一处查看大纲、人物设定、实际剧情状态、关系和时间线。</p>
      </div>
      <div class="planning-actions">
        <div class="count-badges">
          <StatusBadge
            v-for="(count, kind) in workspace.counts"
            :key="kind"
            :label="`${PLANNING_KIND_LABELS[kind] || kind} ${count}`"
          />
        </div>
        <el-switch v-model="advanced" inline-prompt active-text="高级" inactive-text="简洁" />
        <el-button :icon="Refresh" circle aria-label="刷新策划数据" @click="load" />
      </div>
    </header>

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
      @action="load"
    />

    <template v-else>
      <nav class="canvas-tabs" aria-label="策划视图">
        <el-segmented
          v-model="viewMode"
          :options="[
            { label: '卡片大纲', value: 'cards' },
            { label: '关系图', value: 'relations' },
            { label: '时间线', value: 'timeline' },
            { label: '编辑大纲', value: 'editor' },
          ]"
        />
        <span v-if="advanced" class="advanced-note">高级模式显示数据来源和原始字段</span>
      </nav>

      <div v-if="viewMode === 'editor'" class="legacy-editor">
        <OutlineEditorLegacy />
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
          <PlanningCanvas
            :mode="viewMode"
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
  min-height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-canvas);
}

.planning-header {
  min-height: 86px;
  display: flex;
  justify-content: space-between;
  gap: var(--space-5);
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-surface);
}

.eyebrow { margin: 0 0 3px; color: var(--color-primary); font-size: 11px; font-weight: 800; letter-spacing: .1em; }
.planning-header h1 { margin: 0; color: var(--color-text-strong); font-size: 22px; }
.planning-header p:last-child { margin: 5px 0 0; color: var(--color-text-muted); font-size: 12px; }
.planning-actions { display: flex; align-items: center; justify-content: flex-end; gap: var(--space-3); }
.count-badges { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 5px; }
.planning-warning { border-radius: 0; }

.canvas-tabs {
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: 7px var(--space-4);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-surface);
}
.advanced-note { color: var(--color-text-muted); font-size: 11px; }
.planning-split { flex: 1; min-height: 580px; }
.legacy-editor { flex: 1; overflow: auto; padding: var(--space-5); }
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
  .planning-header { align-items: stretch; flex-direction: column; }
  .planning-actions { justify-content: space-between; }
  .count-badges { justify-content: flex-start; }
  .planning-split { display: grid; grid-template-rows: auto minmax(460px, 1fr) auto; }
  :deep(.splitpanes__pane) { width: 100% !important; height: auto; }
  :deep(.splitpanes__splitter) { display: none; }
}
</style>
