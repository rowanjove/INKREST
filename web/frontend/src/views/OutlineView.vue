<script setup lang="ts">
import { DocumentAdd, Refresh, Tickets, Warning } from '@element-plus/icons-vue'
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
        <h1>作品大纲</h1>
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
  gap: 10px;
  max-height: calc(100vh - 72px);
  overflow: hidden;
}

.mode-switcher {
  margin-right: 2px;
}

.outline-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.outline-viewport {
  flex: 1;
  min-height: 0;
  overflow: hidden;
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