<script setup lang="ts">
import { DocumentAdd, Refresh, Tickets, Warning } from '@element-plus/icons-vue'

const props = withDefaults(defineProps<{ advanced?: boolean }>(), {
  advanced: false,
})
import OutlineQueueStatus from '../components/workbench/OutlineQueueStatus.vue'
import NovelProgressHelp from '../components/NovelProgressHelp.vue'
import OutlineGenesPanel from '../components/outline/OutlineGenesPanel.vue'
import OutlineMindmapPane from '../components/outline/OutlineMindmapPane.vue'
import OutlineClassicPane from '../components/outline/OutlineClassicPane.vue'
import OutlineDialogs from '../components/outline/OutlineDialogs.vue'
import { useOutlineView } from '../composables/useOutlineView'

const {
  tasksStore,
  loading,
  submitting,
  outline,
  dialogVisible,
  editDialogVisible,
  viewMode,
  form,
  editForm,
  editGenesVisible,
  editGenesForm,
  newGuard,
  customTitle,
  arcQueueStale,
  arcSyncLoading,
  genreGenes,
  title,
  logline,
  genre,
  protagonist,
  arcs,
  promises,
  targetChapters,
  displayIndex,
  connections,
  setNodeRef,
  load,
  syncArcQueue,
  submitOutline,
  openEditDialog,
  selectChosenTitle,
  saveOutlineBasics,
  openEditGenes,
  addGuard,
  removeGuard,
  handleSaveGenes,
} = useOutlineView()
</script>

<template>
  <section class="outline-page" v-loading="loading">
    <header class="page-head">
      <div class="page-title-area">
        <h1>经典大纲编辑</h1>
        <p>设定小说大纲、题材定位、爽点机制与篇章规划。</p>
      </div>
      <div class="head-actions">
        <el-segmented
          v-model="viewMode"
          :options="[
            { label: '思维导图', value: 'mindmap' },
            { label: '传统视图', value: 'classic' }
          ]"
          class="mode-switcher"
          size="small"
        />
        <el-button size="small" :icon="Refresh" @click="load">刷新</el-button>
        <el-button size="small" :disabled="!outline || tasksStore.isRunning" @click="openEditDialog">编辑设定</el-button>
        <el-button
          size="small"
          type="primary"
          :icon="DocumentAdd"
          :disabled="tasksStore.isRunning"
          @click="dialogVisible = true"
        >
          {{ outline ? '更新大纲' : '生成大纲' }}
        </el-button>
      </div>
    </header>

    <!-- 卷纲 / 阶段概览（置于页头后、进度数字前） -->
    <section v-if="outline && arcs && arcs.length" class="arcs-overview-panel">
      <div class="arcs-overview-head">
        <div class="head-left">
          <h3>卷纲 / 阶段概览</h3>
          <el-tag size="small" type="info" effect="plain">{{ arcs.length }} 个阶段</el-tag>
          <span v-if="props.advanced" class="adv-tag">来源: workspace/outline.json</span>
        </div>
      </div>
      <div class="arcs-scroll">
        <div class="arcs-list">
          <article v-for="(arc, index) in arcs" :key="index" class="arc-card">
            <span class="phase-tag">Phase {{ displayIndex(index) }}</span>
            <strong class="arc-title">{{ arc.title || arc.name || `阶段 ${displayIndex(index)}` }}</strong>
            <p class="arc-desc">{{ arc.summary || arc.description || arc.goal || arc }}</p>
          </article>
        </div>
      </div>
    </section>

    <NovelProgressHelp />

    <OutlineQueueStatus v-if="outline" />

    <el-alert
      v-if="arcQueueStale?.stale"
      type="warning"
      :closable="false"
      show-icon
      class="arc-stale-alert"
      :title="arcQueueStale?.message || '宏观卷纲与卷队列可能不一致'"
    >
      <template #default>
        <el-button
          size="small"
          type="primary"
          :loading="arcSyncLoading"
          :disabled="tasksStore.isRunning || arcSyncLoading"
          @click="syncArcQueue"
        >
          同步卷队列
        </el-button>
      </template>
    </el-alert>

    <div v-if="outline && !outline.chosen_title" class="title-pick-bar">
      <span class="pick-label"><el-icon><Warning /></el-icon> 请确定小说最终名称（确定后开始生成）：</span>
      <div class="pick-options">
        <button
          v-for="opt in (outline.title_options || [])"
          :key="opt"
          class="pick-pill"
          @click="selectChosenTitle(opt)"
        >
          {{ opt }}
        </button>
        <el-input
          v-model="customTitle"
          placeholder="输入自定义名称..."
          size="small"
          style="width: 210px;"
          @keyup.enter="selectChosenTitle(customTitle)"
        >
          <template #append>
            <el-button size="small" @click="selectChosenTitle(customTitle)">确定</el-button>
          </template>
        </el-input>
      </div>
    </div>

    <div v-if="outline" class="outline-body">
      <OutlineGenesPanel :genre-genes="genreGenes" :on-open-edit-genes="openEditGenes" />

      <div class="outline-viewport">
        <OutlineMindmapPane
          v-if="viewMode === 'mindmap'"
          :title="title"
          :genre="genre"
          :target-chapters="targetChapters"
          :arcs="arcs"
          :connections="connections"
          :set-node-ref="setNodeRef"
          :display-index="displayIndex"
        />
        <OutlineClassicPane
          v-else
          :outline="outline"
          :title="title"
          :logline="logline"
          :genre="genre"
          :target-chapters="targetChapters"
          :protagonist="protagonist"
          :promises="promises"
          :arcs="arcs"
          :display-index="displayIndex"
        />
      </div>
    </div>

    <section v-else-if="!loading" class="empty-outline">
      <el-icon><Tickets /></el-icon>
      <h2>还没有作品大纲</h2>
      <p>生成大纲后，这里会展示书名、卖点、主角脑图和卷纲，工作台只负责运行章节。</p>
      <el-button type="primary" :icon="DocumentAdd" @click="dialogVisible = true">生成大纲</el-button>
    </section>

    <OutlineDialogs
      v-model:dialog-visible="dialogVisible"
      v-model:edit-dialog-visible="editDialogVisible"
      v-model:edit-genes-visible="editGenesVisible"
      v-model:form="form"
      v-model:edit-form="editForm"
      v-model:edit-genes-form="editGenesForm"
      v-model:new-guard="newGuard"
      :outline="outline"
      :submitting="submitting"
      :tasks-running="tasksStore.isRunning"
      :on-submit-outline="submitOutline"
      :on-save-outline-basics="saveOutlineBasics"
      :on-add-guard="addGuard"
      :on-remove-guard="removeGuard"
      :on-save-genes="handleSaveGenes"
    />
  </section>
</template>

<style scoped>
.outline-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.mode-switcher {
  margin-right: 2px;
}

.arcs-overview-panel {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg, 8px);
  background: var(--color-bg-surface);
  padding: 12px 14px;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03);
}

.arcs-overview-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.head-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.head-left h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: var(--color-text-strong);
}

.adv-tag {
  font-size: 11px;
  color: var(--color-text-muted);
  font-family: ui-monospace, monospace;
}

.arcs-scroll {
  overflow-x: auto;
  padding-bottom: 4px;
}

.arcs-list {
  display: flex;
  gap: 10px;
}

.arcs-list .arc-card {
  min-width: 220px;
  max-width: 320px;
  flex: 1;
  border: 1px solid var(--color-border-subtle, #e2e8f0);
  border-radius: var(--radius-md, 6px);
  padding: 10px 12px;
  background: var(--color-bg-surface-muted, #f8fafc);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.phase-tag {
  font-size: 11px;
  font-weight: 700;
  color: var(--color-primary, #2563eb);
}

.arc-title {
  font-size: 13px;
  color: var(--color-text-strong);
}

.arc-desc {
  margin: 0;
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.outline-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.outline-viewport {
  min-height: 420px;
  display: flex;
  flex-direction: column;
}

.empty-outline {
  display: grid;
  justify-items: center;
  gap: 10px;
  padding: 48px 24px;
  text-align: center;
  flex: 1;
  border: 1px solid #e1e7ef;
  border-radius: 8px;
  background: var(--color-bg-surface);
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04);
}

.empty-outline .el-icon {
  color: #c66f4f;
  font-size: 42px;
}

.empty-outline h2 {
  margin: 0;
  color: #111827;
}

.empty-outline p {
  max-width: 560px;
  margin: 0;
  color: var(--color-text-muted);
}

.title-pick-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: #fdfaf2;
  border: 1px solid #f2e3d0;
  border-radius: 8px;
  padding: 8px 12px;
  flex-shrink: 0;
}

.pick-label {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #a55236;
  font-weight: 700;
  font-size: 14px;
}

.pick-options {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.pick-pill {
  border: 1px solid #f0c9b7;
  background: var(--color-bg-surface);
  color: #9a5033;
  border-radius: 999px;
  padding: 5px 12px;
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
  transition: all 0.2s ease;
}

.pick-pill:hover {
  background: #fff4ee;
  color: #c66f4f;
  border-color: #c66f4f;
  transform: translateY(-1px);
}
</style>
