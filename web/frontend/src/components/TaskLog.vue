<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Clock, DataLine, Refresh } from '@element-plus/icons-vue'
import EmptyStatePanel from './EmptyStatePanel.vue'
import { getTaskQueue, type TaskQueueSnapshot } from '../api'
import { useTasksStore } from '../stores/tasks'
import { formatTaskStep } from '../utils/taskStepLabels'

const tasksStore = useTasksStore()
const { taskList: tasks } = storeToRefs(tasksStore)
const refreshing = ref(false)
const queueSnapshot = ref<TaskQueueSnapshot | null>(null)

async function refreshTasks() {
  const [, queueRes] = await Promise.all([
    tasksStore.refreshTaskList(),
    getTaskQueue().catch(() => ({ data: null })),
  ])
  queueSnapshot.value = queueRes.data
}

async function handleRefresh() {
  refreshing.value = true
  try {
    await refreshTasks()
  } finally {
    refreshing.value = false
  }
}

onMounted(() => {
  void refreshTasks()
})

const router = useRouter()

const formatTime = (timeStr?: string) => {
  if (!timeStr) return ''
  try {
    let dateStr = timeStr
    if (!timeStr.includes('T') && !timeStr.includes('Z')) {
      dateStr = timeStr.replace(' ', 'T') + 'Z'
    }
    const date = new Date(dateStr)
    if (!isNaN(date.getTime())) {
      const pad = (n: number) => String(n).padStart(2, '0')
      return `${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
    }
  } catch (e) {}
  return timeStr
}

const handleTaskClick = (task: any) => {
  if (task.status === 'failed' && task.chapter_id) {
    router.push({ name: 'chapter-detail', params: { id: task.chapter_id } })
  }
}

const formatStatus = (status: string) => {
  switch (status) {
    case 'pending': return '排队中'
    case 'claimed': return '已认领'
    case 'running': return '执行中'
    case 'paused': return '已暂停'
    case 'succeeded': return '已完成'
    case 'failed': return '已失败'
    case 'cancelled': return '已取消'
    default: return status
  }
}

const queueSummary = computed(() => {
  const q = queueSnapshot.value
  if (!q) return ''
  const parts = [
    `并发上限 ${q.max_concurrent_chapters} 章`,
    `活跃任务 ${q.active_task_count}`,
  ]
  if (q.running_chapters?.length) {
    parts.push(`运行中：第 ${q.running_chapters.join('、')} 章`)
  }
  if (q.novel_batch_task_id) {
    parts.push('全书连写任务进行中')
  }
  return parts.join(' · ')
})

const failureStats = computed(() => {
  const recent = tasks.value.slice(0, 50)
  const counts = new Map<string, number>()
  for (const task of recent) {
    if (task.status !== 'failed') continue
    const meta = task as { failure_kind?: string; error_code?: string; error?: string }
    const key = String(meta.failure_kind || meta.error_code || meta.error || 'unknown').slice(0, 40)
    counts.set(key, (counts.get(key) || 0) + 1)
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([kind, count]) => ({ kind, count }))
})

const formatTaskTitle = (task: any) => {
  if (task.task_id?.startsWith('novel-')) return '整本自动生成'
  return `章节 ${task.chapter_id || '-'}`
}

const getProgressMessage = (task: any) => {
  if (task.status === 'running' && task.progress) {
    const stepName = formatTaskStep(task.progress.step)
    let detail = ''
    if (task.progress.data) {
      if (task.progress.step === 'writer') {
        const sceneId = task.progress.data.scene_id
        const sceneCount = task.progress.data.scene_count
        if (sceneId) {
          detail = ` (正在写入场景: ${sceneId})`
        } else if (sceneCount) {
          detail = ` (共 ${sceneCount} 个场景)`
        }
      } else if (task.progress.step === 'planner') {
        const count = task.progress.data.scenes || 0
        detail = count ? ` (规划出 ${count} 个场景)` : ''
      } else if (task.progress.step === 'auditor') {
        const risk = task.progress.data.risk_level || ''
        detail = risk ? ` (风险评级: ${risk})` : ''
      } else if (task.progress.step === 'vector_index' && task.progress.status === 'skipped') {
        detail = task.progress.data?.reason === 'vector_disabled'
          ? ' (短篇体量已关闭语义检索)'
          : ''
      } else if (task.progress.step === 'quality_guard') {
        if (task.progress.status === 'blocked') {
          detail = ' (未通过，已暂停落库)'
        } else if (task.progress.data?.mode === 'block_on_fail') {
          detail = ' (严格模式)'
        }
      } else if (task.progress.step === 'plugin_hook' && task.progress.status === 'warning') {
        const hook = task.progress.data?.hook || ''
        detail = hook ? ` (插件 ${hook} 执行失败)` : ' (插件执行失败)'
      }
    }
    const statusSuffix =
      task.progress?.status === 'skipped'
        ? ' [已跳过]'
        : task.progress?.status === 'warning'
          ? ' [告警]'
          : task.progress?.status === 'blocked'
            ? ' [阻断]'
            : ''
    return `当前进度：${stepName}${detail}${statusSuffix}...`
  }
  return task.error || task.goal || '排队中...'
}

const recoveryMessage = (task: any) => {
  const parts = []
  if (task.status_reason) parts.push(`Reason: ${task.status_reason}`)
  if (task.resumable_from) parts.push(`Resume: ${task.resumable_from}`)
  if (task.last_heartbeat) parts.push(`Heartbeat: ${formatTime(task.last_heartbeat)}`)
  return parts.join(' · ')
}
</script>

<template>
  <section class="panel task-log-panel">
    <div class="panel-header">
      <h2 class="panel-title">任务流水日志</h2>
      <div class="panel-header-actions">
        <span v-if="queueSummary" class="queue-summary muted">{{ queueSummary }}</span>
        <span class="muted">{{ tasks.length }} 条记录</span>
        <el-button
          size="small"
          :icon="Refresh"
          :loading="refreshing"
          @click="handleRefresh"
        >
          刷新
        </el-button>
      </div>
    </div>
    <div v-if="failureStats.length" class="failure-stats">
      <span class="failure-stats-label">近 50 条失败分类：</span>
      <el-tag
        v-for="row in failureStats"
        :key="row.kind"
        size="small"
        type="danger"
        effect="plain"
        class="failure-tag"
      >
        {{ row.kind }} × {{ row.count }}
      </el-tag>
    </div>
    <div class="task-timeline-container">
      <div v-if="tasks.length > 0" class="timeline-list">
        <div v-for="task in tasks" :key="task.task_id" class="timeline-item">
          <div class="timeline-node">
            <span class="status-dot-inner" :class="task.status"></span>
            <div class="timeline-line"></div>
          </div>
          <div
            class="timeline-content"
            :class="{ 'clickable-failed': task.status === 'failed' && task.chapter_id }"
            @click="handleTaskClick(task)"
          >
            <div class="timeline-meta">
              <div style="display: flex; align-items: center; gap: 8px;">
                <span class="chapter-tag">{{ formatTaskTitle(task) }}</span>
                <span class="task-time" v-if="task.created_at">{{ formatTime(task.created_at) }}</span>
              </div>
              <span class="status-label" :class="task.status">{{ formatStatus(task.status) }}</span>
            </div>
            <p class="task-message">{{ getProgressMessage(task) }}</p>
            <p v-if="recoveryMessage(task)" class="task-recovery">{{ recoveryMessage(task) }}</p>
          </div>
        </div>
      </div>
      <EmptyStatePanel
        v-else
        :icon="Clock"
        title="暂无任务流水记录"
        description="请在工作台「连写启动」后回到此处查看；修章见章节维护。"
        :actions="[
          { label: '去工作台连写', type: 'primary', icon: DataLine, onClick: () => router.push('/workspace') },
          { label: '刷新', plain: true, icon: Refresh, onClick: handleRefresh },
        ]"
      />
    </div>
  </section>
</template>

<style scoped>
.failure-stats {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 10px 24px 0;
}
.failure-stats-label {
  font-size: 12px;
  color: var(--color-text-subtle);
}
.failure-tag { margin: 0; }
.empty-hint {
  margin: 8px 0 0;
  font-size: 13px;
  color: var(--color-text-subtle);
}
.task-log-panel { display: flex; flex-direction: column; height: 100%; min-height: 0; }
.task-timeline-container { flex: 1; min-height: 0; padding: 24px; overflow-y: auto; }
.panel-header-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.queue-summary { font-size: 12px; }
.timeline-list { display: flex; flex-direction: column; }
.timeline-item { display: flex; gap: 16px; }
.timeline-node { display: flex; flex-direction: column; align-items: center; width: 16px; }
.status-dot-inner {
  width: 10px; height: 10px; border-radius: 50%; background: #909399; z-index: 2;
}
.status-dot-inner.succeeded { background: #52c41a; box-shadow: 0 0 6px rgba(82, 196, 26, 0.4); }
.status-dot-inner.failed { background: #f56c6c; box-shadow: 0 0 6px rgba(245, 108, 108, 0.4); }
.status-dot-inner.running, .status-dot-inner.pending {
  background: #e6a23c; box-shadow: 0 0 6px rgba(230, 162, 60, 0.4);
  animation: task-pulse 1.5s infinite ease-in-out;
}
@keyframes task-pulse {
  0% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.3); opacity: 0.7; }
  100% { transform: scale(1); opacity: 1; }
}
.timeline-line { width: 2px; flex-grow: 1; background: var(--border-light); margin-top: 4px; margin-bottom: 4px; }
.timeline-item:last-child .timeline-line { display: none; }
.timeline-content { flex-grow: 1; padding-bottom: 20px; display: flex; flex-direction: column; gap: 4px; }
.timeline-meta { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.chapter-tag { font-size: 13px; font-weight: 700; color: #1a2129; }
.status-label { font-size: 11px; font-weight: 600; padding: 2px 6px; border-radius: 4px; }
.status-label.succeeded { background: #f0f9eb; color: #52c41a; }
.status-label.failed { background: #fef0f0; color: #f56c6c; }
.status-label.running, .status-label.pending { background: #fdf6ec; color: #e6a23c; }
.task-message { font-size: 13px; color: var(--text-muted); line-height: 1.5; }
.task-recovery { margin: 0; font-size: 12px; color: var(--color-text-subtle); line-height: 1.45; }
.empty-state-card {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 12px; padding: 40px; color: var(--text-muted); text-align: center;
}
.empty-icon { font-size: 32px; color: #c4cbd2; }
.timeline-content.clickable-failed {
  cursor: pointer;
  transition: all 0.2s ease;
  padding: 4px 8px;
  border-radius: 6px;
}
.timeline-content.clickable-failed:hover {
  background: rgba(245, 108, 108, 0.05);
}
.timeline-content.clickable-failed:hover .chapter-tag {
  text-decoration: underline;
  color: #f56c6c;
}
.task-time {
  font-size: 11px;
  color: var(--text-muted);
}
</style>
