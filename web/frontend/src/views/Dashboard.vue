<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { DocumentAdd, Plus } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import DashboardWorkbenchPane from '../components/dashboard/DashboardWorkbenchPane.vue'
import DashboardMetricsPane from '../components/dashboard/DashboardMetricsPane.vue'
import DashboardSerializationPane from '../components/dashboard/DashboardSerializationPane.vue'
import DashboardOutlineDiffDialog from '../components/dashboard/DashboardOutlineDiffDialog.vue'
import DashboardAddChapterDialog from '../components/dashboard/DashboardAddChapterDialog.vue'
import FactoryControlPanel from '../components/workbench/FactoryControlPanel.vue'
import FactoryPipelinePanel from '../components/workbench/FactoryPipelinePanel.vue'
import ProductionPlanPanel from '../components/workbench/ProductionPlanPanel.vue'
import RepairCommandPanel from '../components/workbench/RepairCommandPanel.vue'

import { useDashboardWorkbench } from '../composables/useDashboardWorkbench'
import { useDashboardSerial } from '../composables/useDashboardSerial'
import { useDashboardBatchDialog } from '../composables/useDashboardBatchDialog'
import { useDashboardPolling } from '../composables/useDashboardPolling'
import { useChapterStore } from '../stores/chapter'
import { useFactoryStore } from '../stores/factory'
import type { FactoryMode, FactoryRiskAction, ProductionPlanNextStep } from '../types/factory'
import { apiErrorMessage, rerunChapterGate, rewriteChapter } from '../api'

const router = useRouter()
const chapterStore = useChapterStore()
const factoryStore = useFactoryStore()
const LongformStabilityPanel = defineAsyncComponent(() => import('../components/workbench/LongformStabilityPanel.vue'))
const NaturalnessRiskPanel = defineAsyncComponent(() => import('../components/workbench/NaturalnessRiskPanel.vue'))
const { loading } = storeToRefs(chapterStore)
const {
  dashboard: factoryDashboard,
  loading: factoryLoading,
  savingMode: factorySavingMode,
  error: factoryError,
} = storeToRefs(factoryStore)

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
const productionPlan = computed(() => factoryDashboard.value?.production_plan || null)
const factoryPipeline = computed(() => factoryDashboard.value?.pipeline || [])
const qualitySummary = computed(() => factoryDashboard.value?.quality_summary || null)
const repairSummary = computed(() => factoryDashboard.value?.repair || null)
const stabilityReport = computed(() => factoryDashboard.value?.stability_report || null)
const naturalnessReport = computed(() => factoryDashboard.value?.naturalness_report || null)

function scrollToWorkbenchPipeline() {
  activeTab.value = 'workbench'
  window.setTimeout(() => {
    document.querySelector('.production-line')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, 80)
}

function handleFactoryAction(intent: string) {
  if (intent === 'create') {
    router.push('/create')
    return
  }
  if (intent === 'plan') {
    router.push('/create')
    return
  }
  if (intent === 'monitor') {
    router.push('/monitor')
    return
  }
  if (intent === 'repair') {
    router.push('/chapters/maintenance?expand=alerts')
    return
  }
  if (intent === 'export') {
    activeTab.value = 'serialization'
    return
  }
  scrollToWorkbenchPipeline()
}

function handleProductionPlanNextStep(step: ProductionPlanNextStep) {
  if (step.route) {
    router.push(step.route)
    return
  }
  handleFactoryAction(step.intent)
}

function handleFactoryRiskAction(action: FactoryRiskAction) {
  if (action.intent === 'export') {
    activeTab.value = 'serialization'
    return
  }
  if (action.intent === 'repair') {
    router.push('/chapters/maintenance?expand=alerts')
    return
  }
  if (action.intent === 'chapter' || action.route.startsWith('/chapters/')) {
    router.push(action.route)
    return
  }
  if (action.route) {
    router.push(action.route)
    return
  }
  handleFactoryAction(action.intent)
}

async function handleFactoryModeChange(mode: FactoryMode) {
  try {
    await factoryStore.saveMode(mode)
    ElMessage.success('生产模式已更新')
  } catch (error: any) {
    ElMessage.error(apiErrorMessage(error, '生产模式保存失败'))
  }
}

async function goRepairChapter(chapterId: string) {
  try {
    await rewriteChapter(chapterId)
    ElMessage.success(`第 ${chapterId} 章已提交自动修复`)
    await Promise.all([factoryStore.refreshDashboard(), tasksStore.refreshTaskList()])
  } catch (error: any) {
    ElMessage.error(apiErrorMessage(error, '自动修复提交失败'))
    router.push(`/chapters/${chapterId}`)
  }
}

function goEditChapter(chapterId: string) {
  router.push(`/writer?chapter=${chapterId}`)
}

async function goRerunGate(chapterId: string) {
  try {
    await rerunChapterGate(chapterId)
    ElMessage.success(`第 ${chapterId} 章已提交门禁重跑`)
    await factoryStore.refreshDashboard()
  } catch (error: any) {
    ElMessage.error(apiErrorMessage(error, '门禁重跑提交失败'))
    router.push(`/chapters/${chapterId}`)
  }
}

function onBatchFinished() {
  void tasksStore.refreshTaskList()
  void factoryStore.refreshDashboard()
  void loadWorkbench(loadSerialData)
}

onMounted(async () => {
  await Promise.all([loadWorkbench(loadSerialData), factoryStore.loadDashboard()])
  restartDashboardTimer()
  watch(() => tasksStore.isRunning, restartDashboardTimer)
  tasksStore.startRuntimeLogPolling()
  window.addEventListener('inkrest-batch-finished', onBatchFinished)
})

onUnmounted(() => {
  window.removeEventListener('inkrest-batch-finished', onBatchFinished)
  stopDashboardPolling()
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

    <div class="factory-first-screen">
      <FactoryControlPanel
        :dashboard="factoryDashboard"
        :loading="factoryLoading"
        :saving-mode="factorySavingMode"
        :error="factoryError"
        @action="handleFactoryAction"
        @refresh="factoryStore.refreshDashboard"
        @mode-change="handleFactoryModeChange"
      />
      <div class="factory-first-screen__grid">
        <ProductionPlanPanel :plan="productionPlan" @next-step="handleProductionPlanNextStep" />
        <FactoryPipelinePanel :steps="factoryPipeline" :quality="qualitySummary" />
      </div>
      <div class="factory-risk-grid">
        <LongformStabilityPanel
          :report="stabilityReport"
          :priority="factoryDashboard?.project.mode === 'longform_stable'"
          @action="handleFactoryRiskAction"
        />
        <NaturalnessRiskPanel
          :report="naturalnessReport"
          :priority="factoryDashboard?.project.mode === 'platform_review'"
          @action="handleFactoryRiskAction"
        />
      </div>
      <RepairCommandPanel
        :repair="repairSummary"
        @repair="goRepairChapter"
        @edit="goEditChapter"
        @rerun-gate="goRerunGate"
      />
    </div>

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

.factory-first-screen {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.factory-first-screen__grid {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
  gap: 12px;
}

.factory-risk-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
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

  .factory-first-screen__grid {
    grid-template-columns: 1fr;
  }

  .factory-risk-grid {
    grid-template-columns: 1fr;
  }
}
</style>
