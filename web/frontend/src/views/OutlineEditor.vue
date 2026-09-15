<script setup lang="ts">
import { DocumentAdd, Refresh, Tickets } from '@element-plus/icons-vue'

const props = withDefaults(defineProps<{ advanced?: boolean }>(), {
  advanced: false,
})
import OutlineIdentityBand from '../components/outline/OutlineIdentityBand.vue'
import OutlineGenesPanel from '../components/outline/OutlineGenesPanel.vue'
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
  form,
  editForm,
  editGenesVisible,
  editGenesForm,
  newGuard,
  customTitle,
  arcQueueStale,
  arcSyncLoading,
  genreGenes,
  logline,
  genre,
  protagonist,
  arcs,
  promises,
  targetChapters,
  designUpperLimit,
  displayIndex,
  load,
  syncArcQueue,
  submitOutline,
  openGenerateDialog,
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
    <template v-if="outline">
      <header class="outline-toolbar">
        <div class="toolbar-left">
          <span class="toolbar-title">作品设定与篇章规划</span>
        </div>
        <div class="head-actions">
          <el-button size="small" :icon="Refresh" @click="load">刷新</el-button>
          <el-button size="small" :disabled="tasksStore.isRunning" @click="openEditDialog">编辑设定</el-button>
          <el-button
            size="small"
            type="primary"
            :icon="DocumentAdd"
            :disabled="tasksStore.isRunning"
            @click="openGenerateDialog"
          >
            更新大纲
          </el-button>
          <el-button
            v-if="arcQueueStale?.stale || arcSyncLoading"
            size="small"
            type="warning"
            :loading="arcSyncLoading"
            :disabled="tasksStore.isRunning || arcSyncLoading"
            @click="syncArcQueue"
          >
            同步卷队列
          </el-button>
        </div>
      </header>

      <!-- 统一小说核心设定板块 (书名身份 + 类型基因 + 基础设定融合) -->
      <section class="outline-unified-card">
        <OutlineIdentityBand
          :chosen-title="outline.chosen_title || ''"
          :logline="logline"
          :title-options="outline.title_options || []"
          :custom-title="customTitle"
          :loading="loading"
          :on-select-title="selectChosenTitle"
          @update:custom-title="customTitle = $event"
        />

        <div class="unified-specs">
          <OutlineGenesPanel :genre-genes="genreGenes" :on-open-edit-genes="openEditGenes" />

          <OutlineClassicPane
            :outline="outline"
            :genre="genre"
            :target-chapters="targetChapters"
            :protagonist="protagonist"
            :promises="promises"
          />
        </div>
      </section>

      <!-- 卷纲 / 阶段概览是策划页唯一的阶段摘要 -->
      <section v-if="arcs && arcs.length" class="arcs-overview-panel">
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

      <el-alert
        v-if="arcQueueStale?.stale"
        type="warning"
        :closable="false"
        show-icon
        class="arc-stale-alert"
        id="arc-queue-sync"
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
    </template>

    <section v-else-if="!loading" class="empty-outline">
      <el-icon><Tickets /></el-icon>
      <h2>还没有作品大纲</h2>
      <p>生成大纲后，这里会展示书名、卖点、主角脑图和卷纲，工作台只负责运行章节。</p>
      <el-button type="primary" :icon="DocumentAdd" @click="openGenerateDialog">生成大纲</el-button>
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
      :design-upper-limit="designUpperLimit"
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

.outline-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 40px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.toolbar-title {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--color-text-strong);
}

.head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.outline-unified-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg, 8px);
  background: var(--color-bg-surface);
  padding: 16px 18px;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.03);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.outline-unified-card :deep(.identity-band) {
  border-bottom: 1px solid var(--color-border-subtle);
  padding-bottom: 12px;
}

.unified-specs {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.outline-unified-card :deep(.config-card),
.outline-unified-card :deep(.main-panel),
.outline-unified-card :deep(.side-panel) {
  border: 1px solid var(--color-border-subtle);
  box-shadow: none;
  background: var(--color-bg-page);
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

.arc-stale-alert {
  border-radius: var(--radius-md, 6px);
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
</style>
