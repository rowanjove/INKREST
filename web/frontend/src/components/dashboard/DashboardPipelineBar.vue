<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import {
  VideoPlay,
  VideoPause,
  Close,
  Loading,
  CircleCheckFilled,
  CircleCloseFilled,
  Timer,
  Right,
  ArrowRight,
} from '@element-plus/icons-vue'
import { PRODUCTION_BLOCKS, PIPELINE_STEP_LABELS } from '../../constants/pipelineDisplay'
import {
  applyRunningPipelineOverlay,
  rawBlockStatus,
  settleGateBlockAfterChapterComplete,
  settleQueueBlockAfterChapterStart,
  type BlockStatus,
  type ProductionBlockView,
} from '../../utils/productionLineBlocks'
import { useTasksStore } from '../../stores/tasks'
import { useNovelBatchRun } from '../../composables/useNovelBatchRun'

const router = useRouter()
const tasksStore = useTasksStore()
const {
  running: batchRunning,
  busy: batchBusy,
  ctx,
  isCircuitPaused,
  activeProductionTask,
  localControlAction,
  openDialog,
  pauseBatchRun,
  resumeBatchRun,
  cancelBatchRun,
} = useNovelBatchRun()

const isPaused = computed(
  () => activeProductionTask.value?.status === 'paused'
    || Boolean(ctx.value.batchPaused)
    || isCircuitPaused.value,
)

const controlAction = computed(() => activeProductionTask.value?.control_action || localControlAction?.value || '')
const isPauseRequested = computed(() => controlAction.value === 'pause_requested')
const isCancelRequested = computed(() => controlAction.value === 'cancel_requested')

const isOperating = computed(
  () => tasksStore.isRunning || batchRunning.value || batchBusy.value,
)

const activeChapterId = computed(() => tasksStore.currentChapterId || ctx.value.lastChapterId || '')

const blocks = computed<ProductionBlockView[]>(() => {
  const entries = tasksStore.progress
  const pipelineBusy = isOperating.value

  const initialBlocks: ProductionBlockView[] = PRODUCTION_BLOCKS.map((block, index) => {
    const status = rawBlockStatus(block.steps, entries)
    const activeEntry = entries.find(
      (e) => block.steps.includes(e.step) && e.status === 'running',
    )
    const detailLabel = activeEntry ? PIPELINE_STEP_LABELS[activeEntry.step] || activeEntry.step : ''
    return {
      id: block.id,
      index,
      status,
      detailLabel,
      chapterId: activeChapterId.value,
      label: block.label,
      desc: block.desc,
      steps: block.steps,
    }
  })

  let result = applyRunningPipelineOverlay(initialBlocks, {
    pipelineBusy,
    entries,
  })

  result = settleQueueBlockAfterChapterStart(result, entries, activeChapterId.value)
  result = settleGateBlockAfterChapterComplete(result, entries, activeChapterId.value)

  if (isPaused.value) {
    result = result.map((b) => {
      if (b.status === 'running') return { ...b, status: 'paused' as BlockStatus }
      return b
    })
  }

  return result
})

const currentRunningDetail = computed(() => {
  const runningBlock = blocks.value.find((b) => b.status === 'running')
  if (runningBlock?.detailLabel) return runningBlock.detailLabel
  if (runningBlock) return runningBlock.label
  if (isOperating.value) return '正在调度'
  return ''
})

async function handleStart() {
  await openDialog()
}

async function handlePause() {
  await pauseBatchRun()
}

async function handleCancel() {
  try {
    await ElMessageBox.confirm('确定要取消当前生成任务吗？已生成的内容会保留。', '取消任务', {
      confirmButtonText: '确定取消',
      cancelButtonText: '继续执行',
      type: 'warning',
    })
    await cancelBatchRun()
  } catch {
    /* 用户关闭或取消弹窗 */
  }
}

async function handleResume() {
  await resumeBatchRun()
}

function goToProduction() {
  router.push('/production')
}
</script>

<template>
  <section class="dashboard-pipeline-bar" aria-label="生产流水线">
    <div class="pipeline-header">
      <div class="header-left">
        <div class="title-badge">
          <span
            class="pulse-indicator"
            :class="{
              active: isOperating && !isPauseRequested && !isCancelRequested,
              transitioning: isPauseRequested || isCancelRequested,
              paused: isPaused,
            }"
          />
          <strong>生产流水线</strong>
        </div>
        <span class="status-summary">
          <template v-if="isCancelRequested">
            <span class="paused-text">正在取消并保存已完成内容…</span>
          </template>
          <template v-else-if="isPauseRequested">
            <span class="paused-text">正在暂停，等待当前模型请求结束…</span>
          </template>
          <template v-else-if="isOperating">
            <span class="active-text">
              <el-icon class="is-loading"><Loading /></el-icon>
              {{ activeChapterId ? `第 ${activeChapterId} 章 · ` : '' }}{{ currentRunningDetail }}中...
            </span>
          </template>
          <template v-else-if="isPaused">
            <span class="paused-text">
              <el-icon><VideoPause /></el-icon>
              自动生产已暂停{{ ctx.pauseReason ? `（${ctx.pauseReason}）` : '' }}
            </span>
          </template>
          <template v-else>
            <span class="idle-text">空闲就绪 · 点击右侧按钮开启生成</span>
          </template>
        </span>
      </div>

      <div class="header-actions">
        <div class="action-buttons">
          <template v-if="isOperating">
            <el-button
              type="warning"
              plain
              size="default"
              :icon="VideoPause"
              :disabled="isPauseRequested || isCancelRequested"
              @click="handlePause"
            >
              暂停
            </el-button>
            <el-button
              type="danger"
              plain
              size="default"
              :icon="Close"
              :disabled="isCancelRequested"
              @click="handleCancel"
            >
              取消
            </el-button>
          </template>
          <template v-else-if="isPaused">
            <el-button
              type="primary"
              size="default"
              :icon="VideoPlay"
              @click="handleResume"
            >
              继续生产
            </el-button>
            <el-button
              type="info"
              plain
              size="default"
              :icon="Close"
              @click="handleCancel"
            >
              取消
            </el-button>
          </template>
          <template v-else>
            <el-button
              type="primary"
              size="default"
              :icon="VideoPlay"
              @click="handleStart"
            >
              开始生产
            </el-button>
          </template>
        </div>

        <el-button link type="primary" class="detail-link" @click="goToProduction">
          详细编辑 / 日志
          <el-icon><ArrowRight /></el-icon>
        </el-button>
      </div>
    </div>

    <!-- 流水线格子展示 -->
    <div class="pipeline-grid">
      <template v-for="(block, idx) in blocks" :key="block.id">
        <div
          class="step-block"
          :class="[
            `status-${block.status}`,
            { 'is-current': block.status === 'running' }
          ]"
        >
          <div class="step-top">
            <span class="step-num">0{{ idx + 1 }}</span>
            <span class="step-name">{{ block.label }}</span>
          </div>

          <div class="step-status">
            <!-- 运行中：转圈圈 -->
            <template v-if="block.status === 'running'">
              <el-icon class="icon-running is-loading"><Loading /></el-icon>
              <span class="status-label highlight">
                {{ block.detailLabel || '运行中...' }}
              </span>
            </template>
            <!-- 完成：绿色对勾 -->
            <template v-else-if="block.status === 'done'">
              <el-icon class="icon-done"><CircleCheckFilled /></el-icon>
              <span class="status-label success">已完成</span>
            </template>
            <!-- 暂停 -->
            <template v-else-if="block.status === 'paused'">
              <el-icon class="icon-paused"><VideoPause /></el-icon>
              <span class="status-label warning">已暂停</span>
            </template>
            <!-- 出错/阻断 -->
            <template v-else-if="block.status === 'error'">
              <el-icon class="icon-error"><CircleCloseFilled /></el-icon>
              <span class="status-label danger">已阻断</span>
            </template>
            <!-- 等待中 -->
            <template v-else>
              <el-icon class="icon-idle"><Timer /></el-icon>
              <span class="status-label idle">等待中</span>
            </template>
          </div>

          <div class="step-desc" :title="block.desc">
            {{ block.desc }}
          </div>
        </div>

        <div v-if="idx < blocks.length - 1" :key="`arrow-${block.id}`" class="step-connector">
          <el-icon><Right /></el-icon>
        </div>
      </template>
    </div>
  </section>
</template>

<style scoped>
.dashboard-pipeline-bar {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 16px 20px;
  margin-bottom: 20px;
  box-shadow: var(--shadow-sm);
  transition: all 0.2s ease;
}

.pipeline-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--color-border-subtle);
  flex-wrap: wrap;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.title-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.title-badge strong {
  font-size: 15px;
  font-weight: 700;
  color: var(--color-text-strong);
}

.pulse-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-text-muted, #94a3b8);
  transition: all 0.2s ease;
}

.pulse-indicator.active {
  background: #3b82f6;
  box-shadow: 0 0 8px rgba(59, 130, 246, 0.6);
  animation: pulse-ring 1.8s infinite;
}

.pulse-indicator.paused {
  background: #f59e0b;
  box-shadow: 0 0 8px rgba(245, 158, 11, 0.6);
  animation: none !important;
  transform: none !important;
}

.pulse-indicator.transitioning {
  background: #f59e0b;
  box-shadow: 0 0 8px rgba(245, 158, 11, 0.45);
  animation: transition-pulse 0.9s ease-in-out infinite alternate;
}

@keyframes pulse-ring {
  0% { transform: scale(0.95); opacity: 0.8; }
  50% { transform: scale(1.2); opacity: 1; }
  100% { transform: scale(0.95); opacity: 0.8; }
}

@keyframes transition-pulse {
  from { opacity: 0.45; }
  to { opacity: 1; }
}

@media (prefers-reduced-motion: reduce) {
  .pulse-indicator,
  .pulse-indicator.active,
  .pulse-indicator.transitioning,
  .pulse-indicator.paused,
  .icon-running.is-loading,
  .is-loading {
    animation: none !important;
    transition: none !important;
    transform: none !important;
  }
}

.status-summary {
  font-size: 13px;
  color: var(--color-text-muted);
}

.status-summary .active-text {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #2563eb;
  font-weight: 600;
}

.status-summary .paused-text {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #d97706;
  font-weight: 600;
}

.status-summary .idle-text {
  color: var(--color-text-muted);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.action-buttons {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.detail-link {
  font-size: 12.5px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

/* 格子布局 */
.pipeline-grid {
  display: flex;
  align-items: stretch;
  gap: 8px;
  overflow-x: auto;
  padding: 4px 2px;
}

.step-block {
  flex: 1;
  min-width: 130px;
  background: var(--color-bg-surface-muted, #f8fafc);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md, 8px);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}

.step-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.step-num {
  font-size: 11px;
  font-family: monospace;
  color: var(--color-text-muted);
  opacity: 0.8;
}

.step-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-strong);
}

.step-status {
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 22px;
}

.status-label {
  font-size: 12px;
  line-height: 1.2;
}

.status-label.highlight {
  color: #2563eb;
  font-weight: 600;
}

.status-label.success {
  color: #16a34a;
  font-weight: 600;
}

.status-label.warning {
  color: #d97706;
  font-weight: 600;
}

.status-label.danger {
  color: #dc2626;
  font-weight: 600;
}

.status-label.idle {
  color: var(--color-text-muted);
}

/* 图标样式 */
.icon-running {
  color: #2563eb;
  font-size: 15px;
}

.icon-done {
  color: #16a34a;
  font-size: 15px;
}

.icon-paused {
  color: #d97706;
  font-size: 15px;
}

.icon-error {
  color: #dc2626;
  font-size: 15px;
}

.icon-idle {
  color: var(--color-text-muted);
  font-size: 14px;
}

.step-desc {
  font-size: 11px;
  color: var(--color-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: 2px;
}

/* 状态高亮与卡片风格 */
.step-block.status-running {
  background: linear-gradient(135deg, rgba(239, 246, 255, 0.9) 0%, rgba(219, 234, 254, 0.4) 100%);
  border-color: #93c5fd;
  box-shadow: 0 2px 10px rgba(59, 130, 246, 0.12);
  transform: translateY(-1px);
}

.step-block.status-done {
  background: linear-gradient(135deg, rgba(240, 253, 244, 0.8) 0%, rgba(220, 252, 231, 0.3) 100%);
  border-color: #bbf7d0;
}

.step-block.status-paused {
  background: rgba(254, 243, 199, 0.5);
  border-color: #fde68a;
}

.step-block.status-error {
  background: rgba(254, 242, 242, 0.7);
  border-color: #fecaca;
}

/* 步骤之间的连接箭头 */
.step-connector {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-muted);
  opacity: 0.4;
  font-size: 14px;
  padding: 0 2px;
}

@media (max-width: 900px) {
  .pipeline-grid {
    flex-wrap: nowrap;
  }
  .pipeline-header {
    flex-direction: column;
    align-items: flex-start;
  }
  .header-actions {
    width: 100%;
    justify-content: space-between;
  }
}
</style>
