<script setup lang="ts">
import { computed, defineAsyncComponent, h, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { DocumentAdd, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElNotification } from 'element-plus'
import DashboardWorkbenchPane from '../components/dashboard/DashboardWorkbenchPane.vue'
import DashboardMetricsPane from '../components/dashboard/DashboardMetricsPane.vue'
import DashboardSerializationPane from '../components/dashboard/DashboardSerializationPane.vue'
import DashboardOutlineDiffDialog from '../components/dashboard/DashboardOutlineDiffDialog.vue'
import DashboardAddChapterDialog from '../components/dashboard/DashboardAddChapterDialog.vue'


import { useDashboardWorkbench } from '../composables/useDashboardWorkbench'
import { useDashboardSerial } from '../composables/useDashboardSerial'
import { useDashboardBatchDialog } from '../composables/useDashboardBatchDialog'
import { useDashboardPolling } from '../composables/useDashboardPolling'
import { useChapterStore } from '../stores/chapter'
import { useFactoryStore } from '../stores/factory'
import type { FactoryMode, FactoryRiskAction, ProductionPlanNextStep } from '../types/factory'
import { apiErrorMessage, updateAuthorLabel } from '../api'
import { useFactoryActions } from '../composables/useFactoryActions'
import { useNovelBatchRun } from '../composables/useNovelBatchRun'
import { useFactoryAdvancedView } from '../composables/useFactoryAdvancedView'

const router = useRouter()
const route = useRoute()
const chapterStore = useChapterStore()
const factoryStore = useFactoryStore()
const FactoryControlPanel = defineAsyncComponent(() => import('../components/workbench/FactoryControlPanel.vue'))
const FactoryPipelinePanel = defineAsyncComponent(() => import('../components/workbench/FactoryPipelinePanel.vue'))
const ProductionPlanPanel = defineAsyncComponent(() => import('../components/workbench/ProductionPlanPanel.vue'))
const RepairCommandPanel = defineAsyncComponent(() => import('../components/workbench/RepairCommandPanel.vue'))
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
  vectorReadiness,
  serverReadiness,
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
const savingAuthorLabel = ref(false)
const { showAdvanced: showFactoryAdvanced, toggleFactoryAdvanced, expandFactoryAdvanced } =
  useFactoryAdvancedView(factoryDashboard)
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

const { openDialog: openBatchRunDialog } = useNovelBatchRun()

function continueProduction() {
  scrollToWorkbenchPipeline()
  void openBatchRunDialog()
}

const {
  handleFactoryIntent,
  handleFactoryRiskAction,
  repairChapter,
  rerunGate,
} = useFactoryActions({
  navigate: (path) => router.push(path),
  onExport: () => {
    activeTab.value = 'serialization'
  },
  onRun: scrollToWorkbenchPipeline,
})

function handleFactoryAction(intent: string) {
  handleFactoryIntent(intent)
}

function handleProductionPlanNextStep(step: ProductionPlanNextStep) {
  if (step.route) {
    router.push(step.route)
    return
  }
  handleFactoryIntent(step.intent)
}

function applyDashboardDeepLink() {
  if (route.query.tab === 'serialization') {
    activeTab.value = 'serialization'
  }
  if (route.query.focus === 'pipeline') {
    scrollToWorkbenchPipeline()
  }
}

async function handleAuthorLabelChange(label: string) {
  const pid = factoryDashboard.value?.project.id
  if (!pid) return
  savingAuthorLabel.value = true
  try {
    await updateAuthorLabel(pid, label)
    await factoryStore.refreshDashboard()
    ElMessage.success('作者标签已保存')
  } catch (error: any) {
    ElMessage.error(apiErrorMessage(error, '作者标签保存失败'))
  } finally {
    savingAuthorLabel.value = false
  }
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
    await repairChapter(chapterId)
    await Promise.all([factoryStore.refreshDashboard(), tasksStore.refreshTaskList()])
    const notification = ElNotification({
      title: '自动修复已提交',
      type: 'success',
      duration: 8000,
      message: h('div', { class: 'repair-continue-notice' }, [
        h('p', { style: 'margin: 0 0 8px' }, `第 ${chapterId} 章已进入修复队列。`),
        h(
          'button',
          {
            type: 'button',
            style:
              'padding:4px 12px;border:1px solid var(--el-color-success);border-radius:4px;background:var(--el-color-success-light-9);color:var(--el-color-success);cursor:pointer;font-size:13px',
            onClick: () => {
              notification.close()
              continueProduction()
            },
          },
          '继续生产',
        ),
      ]),
    })
    scrollToWorkbenchPipeline()
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
    await rerunGate(chapterId)
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
  applyDashboardDeepLink()
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
        <h1>AI 工厂控制台</h1>
        <p>从灵感到章节产出，监控生产计划、流水线、质量与自动修复。</p>
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
        :saving-author-label="savingAuthorLabel"
        :error="factoryError"
        :show-advanced-details="showFactoryAdvanced"
        @action="handleFactoryAction"
        @refresh="factoryStore.refreshDashboard"
        @mode-change="handleFactoryModeChange"
        @author-label-change="handleAuthorLabelChange"
        @toggle-advanced="toggleFactoryAdvanced"
      />
      <div class="factory-first-screen__grid">
        <ProductionPlanPanel :plan="productionPlan" @next-step="handleProductionPlanNextStep" />
        <FactoryPipelinePanel
          v-if="showFactoryAdvanced"
          :steps="factoryPipeline"
          :quality="qualitySummary"
        />
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
      <div
        v-if="!showFactoryAdvanced && repairSummary?.blocked_count"
        class="factory-repair-compact"
      >
        <span>{{ repairSummary.blocked_count }} 章待修复，展开后可自动修复或改稿。</span>
        <el-button size="small" type="primary" plain @click="expandFactoryAdvanced">
          展开修复中心
        </el-button>
      </div>
      <RepairCommandPanel
        v-if="showFactoryAdvanced"
        :repair="repairSummary"
        @repair="goRepairChapter"
        @edit="goEditChapter"
        @rerun-gate="goRerunGate"
        @continue-production="continueProduction"
      />
    </div>

    <el-tabs v-model="activeTab" class="dashboard-main-tabs">
      <el-tab-pane label="创作工作台" name="workbench" class="tab-pane-workbench">
        <DashboardWorkbenchPane
          :engine-status="engineStatus"
          :outline="outline"
          :assets="assets"
          :max-available-chapters="maxAvailableChapters"
          :vector-readiness="vectorReadiness"
          :server-readiness="serverReadiness"
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
  animation: dashboardFadeIn 0.5s cubic-bezier(0.2, 0.8, 0.2, 1);
}

@keyframes dashboardFadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
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
  gap: 10px;
}

.factory-first-screen__grid {
  display: grid;
  grid-template-columns: minmax(360px, 0.85fr) minmax(0, 1.15fr);
  gap: 10px;
}

.factory-risk-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.factory-first-screen__grid > *, .factory-risk-grid > * {
  transition: transform 0.3s cubic-bezier(0.2, 0.8, 0.2, 1), box-shadow 0.3s ease;
}

.factory-first-screen__grid > *:hover, .factory-risk-grid > *:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-panel);
}

.factory-repair-compact {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--color-alert-danger-border);
  border-radius: var(--radius-md);
  background: var(--glass-bg);
  backdrop-filter: var(--glass-blur);
  color: var(--color-danger);
  font-size: 13px;
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
