<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Refresh, VideoPlay } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  abortTask,
  dismissPipelineAlert,
  rerunChapterGate,
  resumeChapterAudit,
  resumeTask,
  rewriteBatchChapters,
  setChapterExternalReview,
} from '../api'
import { notifyPipelineStarted } from '../utils/pipelineNotify'
import ProductionActionDialog from '../components/production/ProductionActionDialog.vue'
import ProductionCostPanel from '../components/production/ProductionCostPanel.vue'
import ProductionLogsPanel from '../components/production/ProductionLogsPanel.vue'
import ProductionReviewWorkspace from '../components/production/ProductionReviewWorkspace.vue'
import ProductionSummaryStrip from '../components/production/ProductionSummaryStrip.vue'
import ProductionTaskWorkspace from '../components/production/ProductionTaskWorkspace.vue'
import DashboardPipelineBar from '../components/dashboard/DashboardPipelineBar.vue'
import { useNovelBatchRun } from '../composables/useNovelBatchRun'
import { useProductionWorkspace } from '../composables/useProductionWorkspace'
import {
  createProductionActionIntent,
  type ProductionActionIntent,
  type ProductionActionKind,
  type ProductionTask,
} from '../entities/production/production'
import ErrorState from '../shared/ui/ErrorState.vue'
import { useTasksStore } from '../stores/tasks'

const route = useRoute()
const router = useRouter()
const {
  workspace,
  loading,
  error,
  activeTab,
  selectedTaskId,
  selectedChapterId,
  load,
} = useProductionWorkspace()
const { openDialog: openBatchDialog } = useNovelBatchRun()
const tasksStore = useTasksStore()
const actionIntent = ref<ProductionActionIntent | null>(null)
const actionLoading = ref(false)

const batchPaused = computed(
  () => Boolean(workspace.value?.snapshot.chapter_progress.batch_paused),
)
const pauseReason = computed(() => {
  const reason = String(workspace.value?.snapshot.chapter_progress.pause_reason || '')
  if (reason === 'quality_blocked') return '质量门禁阻断'
  if (reason === 'external_review_pending') return '等待外审'
  if (reason === 'consecutive_failures') return '连续失败'
  return reason || '需要人工确认'
})

function openChapter(chapterId: string) {
  void router.push({ path: '/writer', query: { chapter: chapterId } })
}

function openQuality(chapterId: string) {
  void router.push({ path: '/quality', query: { chapter: chapterId } })
}

function requestTaskAction(kind: ProductionActionKind, task: ProductionTask) {
  actionIntent.value = createProductionActionIntent(kind, {
    taskId: task.id,
    chapterIds: task.chapter_id ? [task.chapter_id] : [],
  })
}

function requestReviewAction(
  kind: Exclude<ProductionActionKind, 'cancel_task'>,
  chapterIds: string[],
) {
  actionIntent.value = createProductionActionIntent(kind, { chapterIds })
}

async function runSequential(
  chapterIds: string[],
  action: (chapterId: string) => Promise<unknown>,
) {
  const failures: Array<{ chapterId: string; message: string }> = []
  for (const chapterId of chapterIds) {
    try {
      await action(chapterId)
    } catch (reason: any) {
      failures.push({
        chapterId,
        message: reason?.response?.data?.detail || reason?.message || '请求失败',
      })
    }
  }
  return failures
}

async function confirmAction() {
  const intent = actionIntent.value
  if (!intent || actionLoading.value) return
  actionLoading.value = true
  try {
    let failures: Array<{ chapterId: string; message: string }> = []
    if (intent.kind === 'cancel_task' && intent.taskId) {
      await abortTask(intent.taskId)
    } else if (intent.kind === 'resume_task' && intent.taskId) {
      notifyPipelineStarted({ intent: '恢复任务' })
      await resumeTask(intent.taskId)
    } else if (intent.kind === 'resume_audit') {
      notifyPipelineStarted({ intent: '重跑审计' })
      failures = await runSequential(intent.chapterIds, resumeChapterAudit)
    } else if (intent.kind === 'rerun_gate') {
      notifyPipelineStarted({ intent: '复检门禁' })
      failures = await runSequential(intent.chapterIds, rerunChapterGate)
    } else if (intent.kind === 'rewrite') {
      notifyPipelineStarted({ intent: '重写章节' })
      await rewriteBatchChapters(intent.chapterIds)
    } else if (intent.kind === 'external_passed') {
      failures = await runSequential(intent.chapterIds, (chapterId) =>
        setChapterExternalReview(chapterId, { status: 'external_passed' }),
      )
    } else if (intent.kind === 'dismiss') {
      failures = await runSequential(intent.chapterIds, dismissPipelineAlert)
    }
    actionIntent.value = null
    await load()
    if (failures.length) {
      const succeeded = Math.max(0, intent.chapterIds.length - failures.length)
      ElMessage.warning(
        `${intent.label}：${succeeded} 章成功，${failures.length} 章失败；第 ${failures[0]!.chapterId} 章：${failures[0]!.message}`,
      )
    } else {
      ElMessage.success(`${intent.label}已提交`)
    }
  } catch (reason: any) {
    ElMessage.error(
      reason?.response?.data?.detail || reason?.message || `${intent.label}失败`,
    )
  } finally {
    actionLoading.value = false
  }
}

const handledRouteIntent = ref('')
watch(
  [workspace, () => route.query.intent],
  ([value, intent]) => {
    if (!value) return
    if (typeof intent !== 'string') {
      handledRouteIntent.value = ''
      return
    }
    if (!['novel_continue', 'continue_writing', 'continue-novel', 'run'].includes(intent)) return
    if (handledRouteIntent.value === intent) return
    handledRouteIntent.value = intent
    void openBatchDialog()
    const nextQuery = { ...route.query }
    delete nextQuery.intent
    delete nextQuery.confirm
    void router.replace({ path: route.path, query: nextQuery })
  },
  { immediate: true },
)

onMounted(() => {
  tasksStore.startPolling()
  tasksStore.startRuntimeLogPolling()
})

onUnmounted(() => {
  tasksStore.stopPolling()
  tasksStore.stopRuntimeLogPolling()
})
</script>

<template>
  <section class="production-page" v-loading="loading && !workspace">
    <header class="production-header">
      <div>
        <small>PRODUCTION CONTROL</small>
        <h1>生产中心</h1>
        <p>启动、暂停、恢复与返修都在这里完成；任务历史、费用和日志按需查看。</p>
      </div>
      <div class="header-actions">
        <el-button :icon="Refresh" :loading="loading" @click="load()">刷新</el-button>
        <el-button v-if="activeTab !== 'control'" type="primary" :icon="VideoPlay" @click="activeTab = 'control'">
          返回控制台
        </el-button>
      </div>
    </header>

    <ErrorState
      v-if="error && !workspace"
      title="生产中心加载失败"
      :description="error"
      action-label="重试"
      @action="load()"
    />

    <template v-else-if="workspace">
      <ProductionSummaryStrip :workspace="workspace" />

      <section v-if="batchPaused" class="pause-banner">
        <div>
          <strong>自动生产已暂停：{{ pauseReason }}</strong>
          <span>
            最近章节 {{ workspace.snapshot.chapter_progress.last_chapter_id || '—' }}；
            建议先处理审校队列，再决定是否继续。
          </span>
        </div>
        <el-button type="warning" @click="activeTab = 'reviews'">处理待修章节</el-button>
        <el-button plain @click="openBatchDialog">仍要继续</el-button>
      </section>

      <el-alert
        v-for="(message, section) in workspace.section_errors"
        :key="section"
        type="warning"
        :closable="false"
        show-icon
        :title="message"
      />

      <nav class="production-tabs" aria-label="生产中心分区">
        <button :class="{ active: activeTab === 'control' }" @click="activeTab = 'control'">
          控制台
          <span>{{ batchPaused ? '暂停' : '就绪' }}</span>
        </button>
        <button :class="{ active: activeTab === 'reviews' }" @click="activeTab = 'reviews'">
          审校修复
          <span :class="{ danger: workspace.reviews.summary.open_items }">
            {{ workspace.reviews.summary.open_items }}
          </span>
        </button>
        <button :class="{ active: activeTab === 'runs' }" @click="activeTab = 'runs'">
          任务历史
          <span>{{ workspace.tasks.length }}</span>
        </button>
        <button :class="{ active: activeTab === 'costs' }" @click="activeTab = 'costs'">
          费用
        </button>
        <button :class="{ active: activeTab === 'logs' }" @click="activeTab = 'logs'">
          日志
          <span>{{ workspace.runtime_logs.length }}</span>
        </button>
      </nav>

      <main class="production-canvas">
        <DashboardPipelineBar v-if="activeTab === 'control'" />
        <ProductionTaskWorkspace
          v-else-if="activeTab === 'runs'"
          :tasks="workspace.tasks"
          :events="workspace.events"
          :logs="workspace.task_logs"
          :selected-task-id="selectedTaskId"
          @select="selectedTaskId = $event"
          @action="requestTaskAction"
          @open-chapter="openChapter"
        />
        <ProductionReviewWorkspace
          v-else-if="activeTab === 'reviews'"
          :items="workspace.reviews.items"
          :selected-chapter-id="selectedChapterId"
          @select="selectedChapterId = $event"
          @action="requestReviewAction"
          @open-chapter="openChapter"
          @open-quality="openQuality"
        />
        <ProductionCostPanel
          v-else-if="activeTab === 'costs'"
          :summary="workspace.snapshot.cost_summary"
        />
        <ProductionLogsPanel v-else :logs="workspace.runtime_logs" />
      </main>
    </template>

    <ProductionActionDialog
      :model-value="Boolean(actionIntent)"
      :intent="actionIntent"
      :loading="actionLoading"
      @update:model-value="actionIntent = $event ? actionIntent : null"
      @confirm="confirmAction"
    />
  </section>
</template>

<style scoped>
.production-page {
  display: flex;
  height: 100%;
  min-height: 0;
  flex-direction: column;
  gap: 10px;
  overflow: hidden;
  padding: 14px 16px 16px;
  background: var(--color-bg-page);
}
.production-header { display: flex; flex-shrink: 0; align-items: center; justify-content: space-between; gap: 18px; }
.production-header > div:first-child { display: grid; gap: 3px; }
.production-header small { color: var(--color-primary); font-size: 12px; font-weight: 700; letter-spacing: .08em; }
.production-header h1 { margin: 0; color: var(--color-text-strong); font-size: 24px; line-height: 1.15; }
.production-header p { margin: 0; color: var(--color-text-muted); font-size: 13px; }
.header-actions { display: flex; gap: 8px; }
.pause-banner {
  display: flex; flex-shrink: 0; align-items: center; gap: 9px; padding: 10px 14px;
  border: 1px solid var(--color-alert-warn-border); border-radius: 9px; background: var(--color-alert-warn-bg);
}
.pause-banner > div { display: grid; flex: 1; gap: 2px; }
.pause-banner strong { color: var(--color-text-strong); font-size: 13.5px; }
.pause-banner span { color: var(--color-text-muted); font-size: 12px; }
.production-tabs { display: flex; flex-shrink: 0; align-items: center; gap: 4px; min-height: 42px; padding: 4px; border: 1px solid var(--color-border); border-radius: 10px; background: var(--color-bg-surface); }
.production-tabs button {
  display: inline-flex; align-items: center; gap: 8px; min-height: 34px; padding: 0 15px;
  border: 0; border-radius: 7px; background: transparent; color: var(--color-text-muted); font-size: 13.5px; font-weight: 700; cursor: pointer;
}
.production-tabs button:hover { color: var(--color-text-strong); background: var(--color-bg-hover); }
.production-tabs button.active { color: var(--color-primary); background: var(--color-primary-soft); }
.production-tabs button span { min-width: 18px; padding: 2px 6px; border-radius: 999px; background: var(--color-bg-surface-muted); color: var(--color-text-muted); font-size: 11.5px; font-weight: 600; text-align: center; }
.production-tabs button span.danger { background: var(--color-alert-danger-bg); color: var(--color-danger); }
.production-canvas { flex: 1; min-height: 0; overflow: auto; border: 1px solid var(--color-border); border-radius: var(--radius-lg); background: var(--color-bg-surface); box-shadow: var(--shadow-sm); }
.production-canvas :deep(.dashboard-pipeline-bar) { margin: 0; border: 0; border-radius: 0; box-shadow: none; }
@media (max-width: 900px) {
  .production-page { padding: 10px; }
  .production-header p { display: none; }
  .pause-banner { flex-wrap: wrap; }
}
</style>
