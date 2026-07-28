<script setup lang="ts">
import { computed } from 'vue'
import { RefreshRight } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'

import {
  TASK_STATUS_LABELS,
  type BlockingIssue,
} from '../../entities/project/projectSnapshot'
import { useProjectStore } from '../../stores/project'
import { useProjectSnapshotStore } from '../../stores/projectSnapshot'
import type { BackendStatus } from '../bootstrap/useDesktopLifecycle'
import {
  buildDiagnosticsSummary,
  destinationForAction,
  qualityStatusLabel,
  taskTypeLabel,
} from './diagnostics'

const props = defineProps<{
  modelValue: boolean
  backendStatus: BackendStatus
  backendUnreachable: boolean
}>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()
const router = useRouter()
const projectStore = useProjectStore()
const snapshotStore = useProjectSnapshotStore()

const open = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})
const snapshot = computed(() => snapshotStore.snapshot)
const summary = computed(() =>
  buildDiagnosticsSummary(
    snapshot.value,
    props.backendStatus,
    props.backendUnreachable,
  ),
)
const warningIssues = computed(() =>
  snapshot.value?.blocking_issues.filter((issue) => issue.severity !== 'error') || [],
)
const errorIssues = computed(() =>
  snapshot.value?.blocking_issues.filter((issue) => issue.severity === 'error') || [],
)

function refresh() {
  const projectId = projectStore.currentProject?.id
  if (projectId) void snapshotStore.refresh(projectId, { force: true })
}

async function navigate(path: string) {
  open.value = false
  await router.push(path)
}

function issueDetail(issue: BlockingIssue): string {
  if (issue.detail) return issue.detail
  if (issue.chapter_id) return `关联章节：${issue.chapter_id}`
  return `来源：${issue.source}`
}

function formatUpdatedAt(value: string | undefined): string {
  if (!value) return '尚未同步'
  const timestamp = new Date(value)
  if (Number.isNaN(timestamp.getTime())) return '时间未知'
  return timestamp.toLocaleString('zh-CN', { hour12: false })
}
</script>

<template>
  <el-drawer
    v-model="open"
    class="diagnostics-drawer"
    title="运行诊断"
    size="min(480px, 100vw)"
    append-to-body
  >
    <div class="diagnostics-toolbar">
      <div>
        <span class="diagnostic-state" :class="`diagnostic-state--${summary.tone}`">
          <span aria-hidden="true" />
          {{ summary.label }}
        </span>
        <small>更新于 {{ formatUpdatedAt(snapshot?.updated_at) }}</small>
      </div>
      <el-button
        :icon="RefreshRight"
        :loading="snapshotStore.status === 'loading'"
        aria-label="刷新运行诊断"
        circle
        @click="refresh"
      />
    </div>

    <el-alert
      v-if="backendStatus !== 'online' || backendUnreachable"
      type="error"
      :closable="false"
      title="本地服务暂时不可用"
      description="请检查服务进程；连接恢复后项目状态会自动刷新。"
      show-icon
    />
    <el-alert
      v-else-if="snapshotStore.status === 'error'"
      type="error"
      :closable="false"
      title="项目状态读取失败"
      :description="snapshotStore.error"
      show-icon
    >
      <template #default>
        <el-button size="small" @click="refresh">重试</el-button>
      </template>
    </el-alert>
    <div v-else-if="!snapshot" class="diagnostics-empty">
      <el-skeleton :rows="5" animated />
    </div>

    <template v-else>
      <section class="diagnostic-section" aria-labelledby="diagnostics-overview">
        <h2 id="diagnostics-overview">项目概况</h2>
        <div class="diagnostic-metrics">
          <article>
            <strong>{{ snapshot.chapter_progress.authoritative_completed }}</strong>
            <span>已完成章节</span>
          </article>
          <article>
            <strong>{{ snapshot.outline_progress.planned_chapters }}</strong>
            <span>已规划章节</span>
          </article>
          <article>
            <strong>{{ summary.activeTaskCount }}</strong>
            <span>活跃任务</span>
          </article>
        </div>
      </section>

      <section
        v-if="errorIssues.length"
        class="diagnostic-section"
        aria-labelledby="diagnostics-blockers"
      >
        <h2 id="diagnostics-blockers">需要先处理</h2>
        <article v-for="issue in errorIssues" :key="issue.code" class="diagnostic-item">
          <span class="diagnostic-icon diagnostic-icon--danger" aria-hidden="true">!</span>
          <div>
            <strong>{{ issue.label }}</strong>
            <p>{{ issueDetail(issue) }}</p>
          </div>
        </article>
      </section>

      <section
        v-if="warningIssues.length || snapshot.readiness.warnings.length"
        class="diagnostic-section"
        aria-labelledby="diagnostics-warnings"
      >
        <h2 id="diagnostics-warnings">提醒</h2>
        <article v-for="issue in warningIssues" :key="issue.code" class="diagnostic-item">
          <span class="diagnostic-icon diagnostic-icon--warning" aria-hidden="true">i</span>
          <div>
            <strong>{{ issue.label }}</strong>
            <p>{{ issueDetail(issue) }}</p>
          </div>
        </article>
        <article
          v-for="warning in snapshot.readiness.warnings"
          :key="warning"
          class="diagnostic-item"
        >
          <span class="diagnostic-icon diagnostic-icon--warning" aria-hidden="true">i</span>
          <p>{{ warning }}</p>
        </article>
      </section>

      <section
        v-if="snapshot.active_tasks.length"
        class="diagnostic-section"
        aria-labelledby="diagnostics-tasks"
      >
        <h2 id="diagnostics-tasks">活跃任务</h2>
        <article v-for="task in snapshot.active_tasks" :key="task.id" class="diagnostic-item">
          <span class="diagnostic-icon diagnostic-icon--active" aria-hidden="true" />
          <div>
            <strong>{{ taskTypeLabel(task.task_type) }}</strong>
            <p>
              {{ TASK_STATUS_LABELS[task.status] }} · 第 {{ task.attempt }} /
              {{ task.max_attempts }} 次尝试
            </p>
          </div>
        </article>
      </section>

      <section class="diagnostic-section" aria-labelledby="diagnostics-quality">
        <h2 id="diagnostics-quality">质量与成本</h2>
        <dl class="diagnostic-facts">
          <div>
            <dt>质量状态</dt>
            <dd>{{ qualityStatusLabel(snapshot.quality_summary.status) }}</dd>
          </div>
          <div>
            <dt>通过 / 报告</dt>
            <dd>{{ snapshot.quality_summary.passed }} / {{ snapshot.quality_summary.total_reports }}</dd>
          </div>
          <div>
            <dt>累计用量</dt>
            <dd>{{ snapshot.cost_summary.persisted.total_tokens.toLocaleString('zh-CN') }} tokens</dd>
          </div>
          <div>
            <dt>估算成本</dt>
            <dd>¥{{ snapshot.cost_summary.persisted.total_cost_cny.toFixed(2) }}</dd>
          </div>
        </dl>
        <p v-if="snapshot.cost_summary.disclaimer" class="diagnostic-note">
          {{ snapshot.cost_summary.disclaimer }}
        </p>
      </section>

      <section
        v-if="snapshot.next_actions.some((action) => action.enabled)"
        class="diagnostic-section"
        aria-labelledby="diagnostics-actions"
      >
        <h2 id="diagnostics-actions">建议下一步</h2>
        <button
          v-for="action in snapshot.next_actions.filter((item) => item.enabled)"
          :key="action.id"
          type="button"
          class="diagnostic-action"
          @click="navigate(destinationForAction(action))"
        >
          <span>
            <strong>{{ action.label }}</strong>
            <small>{{ action.kind === 'intent' ? '前往确认页面' : '打开对应页面' }}</small>
          </span>
          <span aria-hidden="true">→</span>
        </button>
      </section>
    </template>
  </el-drawer>
</template>

<style>
.diagnostics-drawer .el-drawer__header {
  margin-bottom: 0;
  padding: 20px 22px 14px;
  border-bottom: 1px solid var(--color-border-subtle);
  color: var(--color-text);
  font-weight: 650;
}

.diagnostics-drawer .el-drawer__body {
  padding: 18px 22px 32px;
}

.diagnostics-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}

.diagnostics-toolbar small {
  display: block;
  margin-top: 5px;
  color: var(--color-text-subtle);
  font-size: 11px;
}

.diagnostic-state {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--color-text);
  font-size: 13px;
  font-weight: 650;
}

.diagnostic-state > span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-success);
}

.diagnostic-state--danger > span { background: var(--color-danger); }
.diagnostic-state--warning > span { background: var(--color-warning); }
.diagnostic-state--active > span { background: var(--color-primary); }
.diagnostic-state--checking > span { background: var(--color-text-subtle); }

.diagnostic-section {
  padding: 20px 0;
  border-bottom: 1px solid var(--color-border-subtle);
}

.diagnostic-section:last-child { border-bottom: 0; }

.diagnostic-section h2 {
  margin: 0 0 12px;
  color: var(--color-text-subtle);
  font-size: 12px;
  font-weight: 650;
  letter-spacing: 0.04em;
}

.diagnostic-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.diagnostic-metrics article {
  padding: 12px;
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  background: var(--color-bg-surface-muted);
}

.diagnostic-metrics strong,
.diagnostic-metrics span {
  display: block;
}

.diagnostic-metrics strong { font-size: 20px; }
.diagnostic-metrics span {
  margin-top: 3px;
  color: var(--color-text-muted);
  font-size: 11px;
}

.diagnostic-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 9px 0;
}

.diagnostic-item strong {
  font-size: 13px;
  font-weight: 600;
}

.diagnostic-item p {
  margin: 3px 0 0;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.5;
}

.diagnostic-icon {
  width: 18px;
  height: 18px;
  display: inline-grid;
  flex: none;
  place-items: center;
  border-radius: 50%;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 11px;
  font-weight: 700;
}

.diagnostic-icon--danger {
  background: var(--color-danger-soft);
  color: var(--color-danger);
}

.diagnostic-icon--warning {
  background: var(--color-warning-soft);
  color: var(--color-warning);
}

.diagnostic-icon--active::after {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-primary);
  content: "";
}

.diagnostic-facts {
  margin: 0;
}

.diagnostic-facts > div {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 7px 0;
}

.diagnostic-facts dt {
  color: var(--color-text-muted);
  font-size: 12px;
}

.diagnostic-facts dd {
  margin: 0;
  color: var(--color-text);
  font-size: 12px;
  font-weight: 600;
}

.diagnostic-note {
  color: var(--color-text-subtle);
  font-size: 11px;
}

.diagnostic-action {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 11px 12px;
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  background: var(--color-bg-surface);
  color: var(--color-text);
  cursor: pointer;
  text-align: left;
}

.diagnostic-action + .diagnostic-action { margin-top: 8px; }
.diagnostic-action:hover { border-color: var(--color-primary); }
.diagnostic-action strong,
.diagnostic-action small { display: block; }
.diagnostic-action small {
  margin-top: 2px;
  color: var(--color-text-subtle);
}

.diagnostics-empty { padding-top: 12px; }
</style>
