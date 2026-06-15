<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import {
  CircleCheck,
  Clock,
  Loading,
  Lightning,
  VideoPause,
  VideoPlay,
  Warning,
} from '@element-plus/icons-vue'
import { PRODUCTION_BLOCKS, PIPELINE_STEP_LABELS } from '../../constants/pipelineDisplay'
import {
  applyRunningPipelineOverlay,
  rawBlockStatus,
  settleGateBlockAfterChapterComplete,
  settleQueueBlockAfterChapterStart,
  type BlockStatus,
} from '../../utils/productionLineBlocks'
import { useNovelBatchRun } from '../../composables/useNovelBatchRun'
import { useTasksStore, type ProgressEntry } from '../../stores/tasks'
import {
  buildReadinessItems,
  readinessAllOk,
  resolveVectorContextFromApis,
  type VectorReadinessContext,
} from '../../utils/projectReadiness'

const props = withDefaults(
  defineProps<{
    engineReady?: boolean
    outline?: Record<string, unknown> | null
    assets?: Array<{ name: string; size?: number }>
    maxAvailableChapters?: number
    vectorReadiness?: VectorReadinessContext
    workScale?: string
    /** 是否显示连写启动等控制区（工作台 true，监控页 false） */
    showControls?: boolean
  }>(),
  {
    engineReady: false,
    outline: null,
    assets: () => [],
    maxAvailableChapters: 0,
    vectorReadiness: () => resolveVectorContextFromApis({}, {}),
    workScale: '',
    showControls: true,
  },
)

const tasksStore = useTasksStore()
const { progress, isRunning, currentChapterId } = storeToRefs(tasksStore)

const {
  cancelBatchRun,
  openDialog,
  opening: batchOpening,
  running: batchRunning,
  busy: batchBusy,
  roundProgress,
} = useNovelBatchRun()

const pausedBlockId = ref<string | null>(null)
const userPaused = ref(false)

const readinessOk = computed(() =>
  readinessAllOk(
    buildReadinessItems({
      engineReady: props.engineReady,
      outline: props.outline,
      assets: props.assets,
      maxAvailableChapters: props.maxAvailableChapters,
      ...props.vectorReadiness,
      workScale: props.workScale,
    }),
  ),
)

const activeChapterId = computed(() => {
  if (currentChapterId.value) return currentChapterId.value
  if (!progress.value.length) return ''
  const sorted = [...progress.value].sort((a, b) => (b.timestamp || 0) - (a.timestamp || 0))
  return sorted[0]?.chapter_id || ''
})

function resolveBlockStatus(blockId: string, steps: string[], entries: ProgressEntry[]): BlockStatus {
  if (userPaused.value && pausedBlockId.value === blockId) return 'paused'
  return rawBlockStatus(steps, entries)
}

const blockViews = computed(() => {
  const chapter = activeChapterId.value
  const entries = chapter
    ? progress.value.filter((p) => p.chapter_id === chapter || !p.chapter_id)
    : progress.value.filter((p) => !p.chapter_id || p.step === 'ensure_queue' || p.step === 'managing_editor')

  let raw = PRODUCTION_BLOCKS.map((block, index) => {
    const status = resolveBlockStatus(block.id, block.steps, entries)
    const runningStep = entries.find(
      (e) => block.steps.includes(e.step) && e.status === 'running',
    )
    const detailStep = runningStep?.step || entries.find((e) => block.steps.includes(e.step))?.step
    return {
      ...block,
      index,
      status,
      detailLabel: detailStep ? PIPELINE_STEP_LABELS[detailStep] || detailStep : '',
      chapterId: runningStep?.chapter_id || (status === 'running' ? chapter : ''),
    }
  })

  raw = settleQueueBlockAfterChapterStart(raw, entries, chapter)
  raw = settleGateBlockAfterChapterComplete(raw, entries, chapter)

  if (userPaused.value) {
    return raw.map((b) => {
      if (b.id === pausedBlockId.value) {
        return { ...b, status: 'paused' as BlockStatus }
      }
      if (b.status === 'running') {
        return {
          ...b,
          status: 'idle' as BlockStatus,
          detailLabel: '',
          chapterId: '',
        }
      }
      return b
    })
  }

  return applyRunningPipelineOverlay(raw, {
    pipelineBusy: isRunning.value || batchBusy.value,
    entries,
  })
})

const pipelineActive = computed(
  () => isRunning.value || batchBusy.value || progress.value.length > 0,
)

const primaryLabel = computed(() => {
  if (userPaused.value) return '继续写书'
  if (batchOpening.value) return '加载开书状态…'
  if (batchRunning.value || isRunning.value) return '连写进行中…'
  return '连写启动'
})

const statusIcon = (status: BlockStatus) => {
  switch (status) {
    case 'running':
      return Loading
    case 'done':
      return CircleCheck
    case 'error':
      return Warning
    case 'paused':
      return VideoPause
    default:
      return Clock
  }
}

async function handlePrimaryStart() {
  userPaused.value = false
  pausedBlockId.value = null
  await openDialog()
}

async function handleBlockAbort(blockId: string) {
  pausedBlockId.value = blockId
  userPaused.value = true
  if (isRunning.value) {
    await tasksStore.abortCurrentTask()
  }
  if (batchBusy.value) {
    cancelBatchRun()
  }
}

async function handleCancelBatch() {
  userPaused.value = false
  pausedBlockId.value = null
  if (isRunning.value) {
    await tasksStore.abortCurrentTask()
  }
  cancelBatchRun()
}

async function handleBlockContinue(blockId: string) {
  pausedBlockId.value = blockId
  userPaused.value = false
  await openDialog()
}

onMounted(() => {
  tasksStore.connectElectronEvents()
})

onUnmounted(() => {
  /* 轮询由工作台 / 日志中心页面生命周期管理，不在此 stop */
})
</script>

<template>
  <section class="pipeline-panel production-line">
    <div class="pipeline-panel__head">
      <div class="pipeline-panel__head-copy">
        <h2 class="pipeline-panel__title">多 Agent 生产线</h2>
        <span class="pipeline-panel__hint">连写按序执行；运行中显示章节号，可中止后续写</span>
      </div>
      <div v-if="showControls" class="head-actions">
        <el-button
          type="success"
          class="batch-run-primary"
          :disabled="!readinessOk || batchOpening || ((batchRunning || isRunning) && !userPaused)"
          @click.stop="handlePrimaryStart"
        >
          <el-icon v-if="batchOpening" class="batch-run-icon is-loading"><Loading /></el-icon>
          <el-icon v-else-if="(batchRunning || isRunning) && !userPaused" class="batch-run-icon is-loading"><Loading /></el-icon>
          <el-icon v-else class="batch-run-icon"><Lightning /></el-icon>
          {{ primaryLabel }}
        </el-button>
        <el-button
          v-if="batchBusy || isRunning"
          type="danger"
          plain
          @click="handleCancelBatch"
        >
          取消连写
        </el-button>
        <span v-if="batchBusy && roundProgress.target > 0" class="round-progress-hint">
          {{ roundProgress.label }}
        </span>
        <span v-if="!readinessOk" class="action-hint">开书清单红灯，请先补齐</span>
      </div>
      <div v-else-if="activeChapterId" class="head-chapter">
        当前章 <strong>第 {{ activeChapterId }} 章</strong>
      </div>
    </div>

    <div class="pipeline-stage-grid pipeline-stage-grid--cols-6" :class="{ active: pipelineActive }">
      <article
        v-for="block in blockViews"
        :key="block.id"
        class="pipeline-stage-card stage-card"
        :class="`status-${block.status}`"
      >
        <div class="pipeline-stage-top">
          <span class="pipeline-stage-index">S{{ block.index + 1 }}</span>
          <el-tag
            v-if="block.status === 'running' && block.chapterId"
            size="small"
            type="warning"
            effect="dark"
            class="chapter-tag"
          >
            第 {{ block.chapterId }} 章
          </el-tag>
        </div>
        <div class="pipeline-stage-icon-row">
          <el-icon :class="{ 'is-loading': block.status === 'running' }">
            <component :is="statusIcon(block.status)" />
          </el-icon>
          <strong>{{ block.label }}</strong>
        </div>
        <p class="pipeline-stage-desc">{{ block.desc }}</p>
        <p v-if="block.detailLabel && block.status === 'running'" class="stage-detail">
          {{ block.detailLabel }}…
        </p>
        <div class="pipeline-stage-actions">
          <el-button
            v-if="block.status === 'running'"
            size="small"
            type="danger"
            plain
            @click="handleBlockAbort(block.id)"
          >
            中止
          </el-button>
          <el-button
            v-else-if="block.status === 'paused' || (userPaused && pausedBlockId === block.id)"
            size="small"
            type="primary"
            :icon="VideoPlay"
            @click="handleBlockContinue(block.id)"
          >
            继续
          </el-button>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.head-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.batch-run-primary .batch-run-icon {
  margin-right: 6px;
  font-size: 16px;
  vertical-align: -2px;
}

.action-hint {
  font-size: 12px;
  color: var(--color-text-subtle);
}

.round-progress-hint {
  font-size: 12px;
  color: var(--color-text-muted);
  font-weight: 600;
}

.head-chapter {
  font-size: 13px;
  color: var(--color-text-muted);
}

.head-chapter strong {
  color: var(--color-primary);
}

.chapter-tag {
  flex-shrink: 0;
  max-width: 100%;
}

.stage-detail {
  margin: 0;
  font-size: 11px;
  color: #b45309;
  font-weight: 600;
}

.stage-card.status-idle {
  background: var(--color-bg-surface-muted);
}

.stage-card.status-running {
  background: #fdf6ec;
  box-shadow: inset 0 0 0 1px rgba(230, 162, 60, 0.35);
}

.stage-card.status-running .pipeline-stage-icon-row .el-icon {
  color: #e6a23c;
}

.stage-card.status-done {
  background: #f0f9eb;
}

.stage-card.status-done .pipeline-stage-icon-row .el-icon {
  color: #52c41a;
}

.stage-card.status-error {
  background: #fef0f0;
}

.stage-card.status-error .pipeline-stage-icon-row .el-icon {
  color: #f56c6c;
}

.stage-card.status-paused {
  background: #f8fafc;
}

.production-line.pipeline-panel {
  overflow: visible;
}

</style>