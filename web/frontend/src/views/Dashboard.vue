<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Refresh } from '@element-plus/icons-vue'
import PageShell from '../shared/ui/PageShell.vue'
import ErrorState from '../shared/ui/ErrorState.vue'
import StatusBadge from '../shared/ui/StatusBadge.vue'
import { useProjectStore } from '../stores/project'
import { useProjectSnapshotStore } from '../stores/projectSnapshot'
import {
  TASK_STATUS_LABELS,
  blockingIssueAction,
  blockingIssueDetail,
  type BlockingIssue,
  type SnapshotAction,
} from '../entities/project/projectSnapshot'
import type { PlanningWorkspace } from '../entities/planning/planningWorkspace'
import type { OutlineQueueStatus } from '../entities/outline/outlineQueueStatus'
import { getOutlineQueueStatus, getPlanningWorkspace } from '../api'
import { resolveSnapshotActionLocation } from '../app/shell/workflowActions'
import DashboardProgressCard from '../components/dashboard/DashboardProgressCard.vue'
import DashboardQueueCard from '../components/dashboard/DashboardQueueCard.vue'
import ProjectProgressDetailsDialog from '../components/dashboard/ProjectProgressDetailsDialog.vue'

const router = useRouter()
const projectStore = useProjectStore()
const snapshotStore = useProjectSnapshotStore()
const { snapshot, status, error } = storeToRefs(snapshotStore)
const planning = ref<PlanningWorkspace | null>(null)
const queue = ref<OutlineQueueStatus | null>(null)
const queueLoading = ref(false)
const queueError = ref('')
const detailsVisible = ref(false)

const completed = computed(() => Number(snapshot.value?.chapter_progress.authoritative_completed || 0))
const target = computed(() => Number(snapshot.value?.outline_progress.target_chapters || 0))
const progress = computed(() => target.value ? Math.min(100, Math.round(completed.value / target.value * 100)) : 0)
const activeTaskCount = computed(() => snapshot.value?.active_tasks.length || 0)
const blockingIssues = computed(() => snapshot.value?.blocking_issues || [])
const primaryAction = computed(() => snapshot.value?.next_actions.find((action) => action.enabled) || null)

const healthTone = computed(() => {
  if (blockingIssues.value.some((issue) => issue.severity === 'error')) return 'danger'
  if (blockingIssues.value.length || snapshot.value?.readiness.warnings.length) return 'warning'
  return 'success'
})
const healthLabel = computed(() => {
  if (healthTone.value === 'danger') return '存在阻塞'
  if (healthTone.value === 'warning') return '需要关注'
  return '状态正常'
})

function issueTone(issue: BlockingIssue): 'danger' | 'warning' | 'info' {
  if (issue.severity === 'error') return 'danger'
  if (issue.severity === 'warning') return 'warning'
  return 'info'
}

function issueStatusLabel(issue: BlockingIssue): string {
  if (issue.severity === 'error') return '阻塞'
  if (issue.severity === 'warning') return '提醒'
  return '信息'
}

function openAction(action: SnapshotAction) {
  if (!action.enabled) return
  router.push(resolveSnapshotActionLocation(action))
}

async function load() {
  const projectId = projectStore.currentProject?.id
  if (!projectId) return
  queueLoading.value = true
  queueError.value = ''
  await Promise.all([
    snapshotStore.refresh(projectId, { force: true }),
    getPlanningWorkspace()
      .then(({ data }) => { planning.value = data })
      .catch(() => { planning.value = null }),
    getOutlineQueueStatus()
      .then(({ data }) => { queue.value = data as OutlineQueueStatus })
      .catch((error: unknown) => {
        queue.value = null
        queueError.value = error instanceof Error ? error.message : '卷计划暂时无法读取'
      })
      .finally(() => { queueLoading.value = false }),
  ])
}

onMounted(load)
</script>

<template>
  <PageShell
    :title="snapshot?.project.name || projectStore.currentProject?.name || '项目概览'"
    description="聚焦项目健康、策划完成度、正文进度和当前阻塞；生产操作统一在生产中心确认。"
    eyebrow="项目概览"
  >
    <template #actions>
      <el-button :icon="Refresh" :loading="status === 'loading'" @click="load">刷新</el-button>
      <el-button v-if="primaryAction" type="primary" @click="openAction(primaryAction)">
        {{ primaryAction.label }}
      </el-button>
    </template>

    <ErrorState
      v-if="status === 'error'"
      title="项目概览加载失败"
      :description="error"
      action-label="重试"
      @action="load"
    />

    <template v-else-if="snapshot">
      <section class="overview-grid">
        <article class="summary-card health-card">
          <div class="card-heading">
            <span>项目健康</span>
            <StatusBadge :label="healthLabel" :tone="healthTone" dot />
          </div>
          <strong>{{ blockingIssues.length }}</strong>
          <p>项阻塞或风险需要处理</p>
        </article>

        <DashboardProgressCard
          :chapter-progress="snapshot.chapter_progress"
          :completed="completed"
          :target="target"
          :percentage="progress"
          :on-open-details="() => { detailsVisible = true }"
        />

        <DashboardQueueCard
          :queue="queue"
          :loading="queueLoading"
          :error="queueError"
          :planning-entity-count="planning?.entities.length || 0"
          :on-retry="load"
          :on-open-details="() => { detailsVisible = true }"
          :on-open-outline="() => router.push('/outline')"
        />

        <article class="summary-card">
          <div class="card-heading"><span>质量状态</span></div>
          <strong>{{ snapshot.quality_summary.passed }}<small> 通过</small></strong>
          <p>{{ snapshot.quality_summary.failed }} 项未通过 · {{ snapshot.quality_summary.total_reports }} 份报告</p>
        </article>
      </section>

      <section class="overview-columns">
        <article class="panel">
          <header><h2>当前阻塞</h2><span>{{ blockingIssues.length }}</span></header>
          <div v-if="blockingIssues.length" class="issue-list">
            <div v-for="issue in blockingIssues" :key="`${issue.code}-${issue.chapter_id || ''}`" class="issue-row">
              <StatusBadge :label="issueStatusLabel(issue)" :tone="issueTone(issue)" />
              <div class="issue-copy">
                <strong>{{ issue.label }}</strong>
                <p>{{ blockingIssueDetail(issue) }}</p>
              </div>
              <el-button
                text
                type="primary"
                @click="router.push(blockingIssueAction(issue).target)"
              >
                {{ blockingIssueAction(issue).label }}
              </el-button>
            </div>
          </div>
          <p v-else class="empty-copy">没有阻塞项，可以继续策划或前往生产中心。</p>
        </article>

        <article class="panel">
          <header><h2>安全的下一步</h2><span>{{ snapshot.next_actions.length }}</span></header>
          <div class="action-list">
            <button
              v-for="action in snapshot.next_actions"
              :key="action.id"
              type="button"
              :disabled="!action.enabled"
              @click="openAction(action)"
            >
              <span>{{ action.label }}</span>
              <small>{{ action.enabled ? (action.kind === 'intent' ? '前往确认' : '打开') : action.reason }}</small>
            </button>
          </div>
        </article>
      </section>

      <section class="panel">
        <header><h2>正在进行的任务</h2><span>{{ activeTaskCount }}</span></header>
        <div v-if="snapshot.active_tasks.length" class="task-list">
          <div v-for="task in snapshot.active_tasks" :key="task.id">
            <StatusBadge :label="TASK_STATUS_LABELS[task.status]" tone="info" dot />
            <span>{{ task.task_type }}</span>
            <small>尝试 {{ task.attempt }}/{{ task.max_attempts }}</small>
          </div>
        </div>
        <p v-else class="empty-copy">当前没有运行中的后台任务。</p>
      </section>

      <ProjectProgressDetailsDialog
        v-model="detailsVisible"
        :progress="snapshot.chapter_progress"
        :queue="queue"
      />
    </template>
  </PageShell>
</template>

<style scoped>
.overview-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-4);
}
.summary-card,
.panel {
  min-width: 0;
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-surface);
  box-shadow: var(--shadow-sm);
}
.card-heading,
.panel header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  color: var(--color-text-muted);
  font-size: 12px;
}
.summary-card > strong { display: block; margin: var(--space-4) 0 5px; color: var(--color-text-strong); font-size: 30px; }
.summary-card strong small { color: var(--color-text-muted); font-size: 13px; font-weight: 500; }
.summary-card p,
.empty-copy { margin: 0; color: var(--color-text-muted); font-size: 12px; line-height: 1.6; }
.overview-columns { display: grid; grid-template-columns: 1.15fr .85fr; gap: var(--space-4); margin: var(--space-4) 0; }
.panel header { margin-bottom: var(--space-4); }
.panel h2 { margin: 0; color: var(--color-text-strong); font-size: 15px; }
.issue-list,
.action-list,
.task-list { display: grid; gap: 8px; }
.issue-row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-3);
  padding: 9px 0;
  border-bottom: 1px solid var(--color-border-subtle);
}
.issue-copy { min-width: 0; display: grid; gap: 3px; }
.issue-copy strong { color: var(--color-text-strong); font-size: 12.5px; line-height: 1.45; overflow-wrap: anywhere; }
.issue-row p { margin: 0; color: var(--color-text-muted); font-size: 11.5px; line-height: 1.45; overflow-wrap: anywhere; }
.action-list button {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
  padding: 10px 12px;
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  background: var(--color-bg-surface-muted);
  color: var(--color-text-strong);
  text-align: left;
  cursor: pointer;
}
.action-list button:disabled { opacity: .55; cursor: not-allowed; }
.action-list small,
.task-list small { color: var(--color-text-muted); }
.task-list > div { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: var(--space-3); }

@media (max-width: 1100px) {
  .overview-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 720px) {
  .overview-grid,
  .overview-columns { grid-template-columns: 1fr; }
}
</style>
