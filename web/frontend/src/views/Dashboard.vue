<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { DocumentAdd, Plus } from '@element-plus/icons-vue'
import DashboardWorkbenchPane from '../components/dashboard/DashboardWorkbenchPane.vue'
import DashboardMetricsPane from '../components/dashboard/DashboardMetricsPane.vue'
import DashboardSerializationPane from '../components/dashboard/DashboardSerializationPane.vue'
import DashboardOutlineDiffDialog from '../components/dashboard/DashboardOutlineDiffDialog.vue'
import DashboardAddChapterDialog from '../components/dashboard/DashboardAddChapterDialog.vue'
import { useNovelBatchRun } from '../composables/useNovelBatchRun'
import { useDashboardWorkbench } from '../composables/useDashboardWorkbench'
import { useDashboardSerial } from '../composables/useDashboardSerial'
import { useDashboardBatchDialog } from '../composables/useDashboardBatchDialog'
import { useDashboardPolling } from '../composables/useDashboardPolling'
import { useChapterStore } from '../stores/chapter'

const router = useRouter()
const chapterStore = useChapterStore()
const { loading } = storeToRefs(chapterStore)

const {
  assets,
  outline,
  engineStatus,
  semanticSearchEffective,
  vectorEnabledForProject,
  form,
  chapterCountTotal,
  calibration,
  scaleProfile,
  allDebt,
  outlineTheme,
  workScale,
  maxAvailableChapters,
  loadWorkbench,
  refreshScaleArchitecture,
} = useDashboardWorkbench()

const {
  serialStatus,
  copyingTrial,
  virtualComments,
  rewritingOutline,
  applyingOutline,
  outlineDiffDialogVisible,
  adaptiveOutlineDiff,
  exportingSerial,
  loadSerialData,
  triggerAdaptiveRewrite,
  applyAdaptive,
  copyTrialForPlatform,
  downloadSerial,
} = useDashboardSerial()

const {
  addChapterDialogVisible,
  addChapterTab,
  batchSubmitting,
  chapterPlanGenerating,
  batchInputMode,
  bulkText,
  chapterPlanCount,
  chapterPlanInstructions,
  batchRows,
  openAddChapterDialog,
  addBatchRow,
  quickAddChapters,
  clearBatchRows,
  importFromBulkText,
  removeBatchRow,
  submitChapter,
  submitBatch,
  fillBatchFromAI,
} = useDashboardBatchDialog({ outline, outlineTheme, form })

const activeTab = ref('workbench')
const { restartDashboardTimer, stopDashboardPolling, tasksStore } = useDashboardPolling({
  activeTab,
  loadSerialData,
})

const { busy: autoRunBusy, dialogVisible: autoRunDialogVisible } = useNovelBatchRun()

watch(autoRunBusy, async (now, prev) => {
  if (prev && !now && !autoRunDialogVisible.value) {
    await loadWorkbench(loadSerialData)
  }
})

onMounted(async () => {
  await loadWorkbench(loadSerialData)
  restartDashboardTimer()
  watch(() => tasksStore.isRunning, restartDashboardTimer)
  tasksStore.connectElectronEvents()
  tasksStore.startPolling()
  tasksStore.startRuntimeLogPolling()
})

onUnmounted(() => {
  stopDashboardPolling()
  tasksStore.stopPolling()
  tasksStore.stopRuntimeLogPolling()
})
</script>

<template>
  <section class="dashboard">
    <header class="page-head">
      <div>
        <h1>工作台</h1>
        <p>触发章节生成、查看产出与长篇指标。</p>
      </div>
      <div class="head-actions">
        <el-button :icon="DocumentAdd" @click="router.push('/outline')">查看大纲</el-button>
        <el-button type="primary" :icon="Plus" :disabled="tasksStore.isRunning" @click="openAddChapterDialog">
          运行单章
        </el-button>
      </div>
    </header>

    <el-tabs v-model="activeTab" class="dashboard-main-tabs">
      <el-tab-pane label="创作工作台" name="workbench" class="tab-pane-workbench">
        <DashboardWorkbenchPane
          :engine-status="engineStatus"
          :outline="outline"
          :assets="assets"
          :max-available-chapters="maxAvailableChapters"
          :semantic-search-effective="semanticSearchEffective"
          :vector-enabled-for-project="vectorEnabledForProject"
          :work-scale="workScale"
          :scale-profile="scaleProfile"
          :chapter-count-total="chapterCountTotal"
          @saved="refreshScaleArchitecture"
        />
      </el-tab-pane>

      <el-tab-pane label="长篇指标" name="metrics" class="tab-pane-metrics">
        <DashboardMetricsPane v-model:active-tab="activeTab" :calibration="calibration" :all-debt="allDebt" />
      </el-tab-pane>

      <el-tab-pane label="连载运营（高级）" name="serialization" class="tab-pane-serialization">
        <DashboardSerializationPane
          :serial-status="serialStatus"
          :virtual-comments="virtualComments"
          :rewriting-outline="rewritingOutline"
          :copying-trial="copyingTrial"
          :exporting-serial="exportingSerial"
          @refresh="loadSerialData"
          @trigger-rewrite="triggerAdaptiveRewrite"
          @copy-trial="copyTrialForPlatform"
          @download="downloadSerial"
        />
      </el-tab-pane>
    </el-tabs>

    <DashboardOutlineDiffDialog
      v-model="outlineDiffDialogVisible"
      :diff="adaptiveOutlineDiff"
      :applying="applyingOutline"
      @apply="applyAdaptive"
    />

    <DashboardAddChapterDialog
      v-model="addChapterDialogVisible"
      v-model:add-chapter-tab="addChapterTab"
      v-model:batch-input-mode="batchInputMode"
      v-model:chapter-plan-count="chapterPlanCount"
      v-model:chapter-plan-instructions="chapterPlanInstructions"
      v-model:bulk-text="bulkText"
      :form="form"
      :batch-rows="batchRows"
      :batch-submitting="batchSubmitting"
      :chapter-plan-generating="chapterPlanGenerating"
      :loading="loading"
      @submit-chapter="submitChapter"
      @submit-batch="submitBatch"
      @fill-batch-from-ai="fillBatchFromAI"
      @add-batch-row="addBatchRow"
      @quick-add-chapters="quickAddChapters"
      @clear-batch-rows="clearBatchRows"
      @import-from-bulk-text="importFromBulkText"
      @remove-batch-row="removeBatchRow"
    />

  </section>
</template>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
}

.head-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.dashboard-main-tabs {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.dashboard-main-tabs :deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.dashboard-main-tabs :deep(.el-tab-pane) {
  height: 100%;
}

.dashboard-main-tabs :deep(.tab-pane-workbench),
.dashboard-main-tabs :deep(.tab-pane-metrics) {
  overflow-x: hidden;
  overflow-y: auto;
  padding-right: 4px;
  padding-bottom: 36px;
  scroll-padding-bottom: 28px;
}

.dashboard-main-tabs :deep(.tab-pane-serialization) {
  overflow-x: hidden;
  overflow-y: auto;
  padding-right: 4px;
  padding-bottom: 40px;
  scroll-padding-bottom: 32px;
}

@media (max-width: 1120px) {
  .page-head {
    align-items: stretch;
    flex-direction: column;
    gap: 12px;
  }
}
</style>