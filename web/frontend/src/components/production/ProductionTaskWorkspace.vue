<script setup lang="ts">
import { computed, ref } from 'vue'
import { useVirtualizer } from '@tanstack/vue-virtual'
import { Search } from '@element-plus/icons-vue'
import type {
  ProductionActionKind,
  ProductionTask,
  ProductionTaskEvent,
  ProductionTaskFilter,
  ProductionTaskLog,
} from '../../entities/production/production'
import {
  filterProductionTasks,
  productionReasonLabel,
  productionStepLabel,
  taskTone,
} from '../../entities/production/production'
import StatusBadge from '../../shared/ui/StatusBadge.vue'

const props = defineProps<{
  tasks: ProductionTask[]
  events: ProductionTaskEvent[]
  logs: ProductionTaskLog[]
  selectedTaskId: string
}>()

const emit = defineEmits<{
  select: [taskId: string]
  action: [kind: ProductionActionKind, task: ProductionTask]
  openChapter: [chapterId: string]
}>()

const query = ref('')
const filter = ref<ProductionTaskFilter>('all')
const scrollElement = ref<HTMLElement | null>(null)
const filtered = computed(() =>
  filterProductionTasks(props.tasks, filter.value, query.value),
)
const selected = computed(
  () =>
    props.tasks.find((task) => task.id === props.selectedTaskId) ||
    props.tasks[0] ||
    null,
)
const selectedEvents = computed(() =>
  props.events.filter((event) => event.task_id === selected.value?.id),
)
const selectedLogs = computed(() =>
  props.logs.filter((row) => row.task_id === selected.value?.id),
)
const virtualizer = useVirtualizer(
  computed(() => ({
    count: filtered.value.length,
    getScrollElement: () => scrollElement.value,
    estimateSize: () => 72,
    overscan: 8,
    getItemKey: (index: number) => filtered.value[index]?.id ?? index,
  })),
)
const virtualRows = computed(() => virtualizer.value.getVirtualItems())
const totalHeight = computed(() => virtualizer.value.getTotalSize())

function formatTime(value: string | null | undefined) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}
</script>

<template>
  <section class="task-workspace">
    <aside class="task-list-pane" aria-label="生产任务列表">
      <header>
        <div><strong>运行与队列</strong><small>{{ filtered.length }} / {{ tasks.length }}</small></div>
        <el-input v-model="query" :prefix-icon="Search" placeholder="搜索任务或章节" clearable />
        <el-segmented
          v-model="filter"
          :options="[
            { label: '全部', value: 'all' },
            { label: '进行中', value: 'active' },
            { label: '失败', value: 'failed' },
            { label: '完成', value: 'finished' },
          ]"
          aria-label="筛选生产任务"
        />
      </header>
      <div ref="scrollElement" class="virtual-scroll">
        <div v-if="filtered.length" class="virtual-list" :style="{ height: `${totalHeight}px` }">
          <button
            v-for="row in virtualRows"
            :key="String(row.key)"
            type="button"
            class="task-row"
            :class="{ active: filtered[row.index]?.id === selected?.id }"
            :style="{ transform: `translateY(${row.start}px)`, height: `${row.size}px` }"
            @click="emit('select', filtered[row.index]!.id)"
          >
            <span class="task-copy">
              <strong>{{ filtered[row.index]!.task_type_label }}</strong>
              <small>
                {{ filtered[row.index]!.chapter_id ? `第 ${filtered[row.index]!.chapter_id} 章 · ` : '' }}
                {{ filtered[row.index]!.step_label || filtered[row.index]!.goal || '等待执行' }}
              </small>
            </span>
            <StatusBadge
              :label="filtered[row.index]!.status_label"
              :tone="taskTone(filtered[row.index]!.status)"
              dot
            />
          </button>
        </div>
        <el-empty v-else description="没有匹配的任务" :image-size="64" />
      </div>
    </aside>

    <article class="task-detail" aria-label="任务详情">
      <template v-if="selected">
        <header class="detail-head">
          <div>
            <small>任务 {{ selected.id }}</small>
            <h2>{{ selected.task_type_label }}</h2>
            <p>
              {{ selected.chapter_id ? `第 ${selected.chapter_id} 章 · ` : '' }}
              尝试 {{ selected.attempt }}/{{ selected.max_attempts }}
            </p>
          </div>
          <StatusBadge :label="selected.status_label" :tone="taskTone(selected.status)" dot />
        </header>

        <div v-if="selected.failure_message" class="failure-card">
          <strong>{{ productionReasonLabel(selected.failure_code) || '任务未完成' }}</strong>
          <p>{{ selected.failure_message }}</p>
        </div>

        <div v-if="selected.warnings?.length" class="warning-card" role="status">
          <strong>正文同步提醒</strong>
          <p v-for="(warning, index) in selected.warnings" :key="`${selected.id}-warn-${index}`">
            {{ warning }}
          </p>
        </div>

        <dl class="task-metadata">
          <div><dt>当前步骤</dt><dd>{{ selected.step_label || '尚未进入流水线' }}</dd></div>
          <div><dt>恢复点</dt><dd>{{ selected.checkpoint.resumable_from ? productionStepLabel(selected.checkpoint.resumable_from) : '无明确恢复点' }}</dd></div>
          <div><dt>最近心跳</dt><dd>{{ formatTime(selected.heartbeat_at) }}</dd></div>
          <div><dt>创建时间</dt><dd>{{ formatTime(selected.created_at) }}</dd></div>
        </dl>

        <div class="task-actions">
          <el-button
            v-if="selected.chapter_id"
            @click="emit('openChapter', selected.chapter_id)"
          >
            打开正文
          </el-button>
          <el-button
            v-if="selected.recovery_action === 'cancel'"
            type="danger"
            plain
            @click="emit('action', 'cancel_task', selected)"
          >
            中止任务
          </el-button>
          <el-button
            v-if="selected.recovery_action === 'resume_audit'"
            type="warning"
            @click="emit('action', 'resume_audit', selected)"
          >
            从审校检查点恢复
          </el-button>
        </div>

        <section class="timeline-section">
          <div class="section-head"><h3>状态时间线</h3><span>{{ selectedEvents.length }} 个事件</span></div>
          <ol v-if="selectedEvents.length" class="event-timeline">
            <li v-for="event in selectedEvents" :key="event.id">
              <span class="event-dot" />
              <div>
                <strong>{{ event.to_status_label }}</strong>
                <p v-if="event.reason">{{ productionReasonLabel(event.reason) }}</p>
                <time>{{ formatTime(event.created_at) }}</time>
              </div>
            </li>
          </ol>
          <p v-else class="empty-copy">尚无持久化状态事件。</p>
        </section>

        <section class="task-log-section">
          <div class="section-head"><h3>任务日志</h3><span>{{ selectedLogs.length }} 条</span></div>
          <ul v-if="selectedLogs.length" class="task-log-list">
            <li v-for="row in selectedLogs" :key="row.id" :class="row.level">
              <time>{{ new Date(row.timestamp * 1000).toLocaleTimeString() }}</time>
              <strong>{{ productionStepLabel(row.step) }}</strong>
              <span>{{ row.message }}</span>
            </li>
          </ul>
          <p v-else class="empty-copy">此任务还没有持久化日志。</p>
        </section>
      </template>
      <el-empty v-else description="尚无生产任务" />
    </article>
  </section>
</template>

<style scoped>
.task-workspace { display: grid; grid-template-columns: minmax(260px, 34%) minmax(0, 1fr); height: 100%; min-height: 0; }
.task-list-pane { display: flex; min-width: 0; min-height: 0; flex-direction: column; border-right: 1px solid var(--color-border); background: var(--color-bg-surface); }
.task-list-pane > header { display: grid; gap: 9px; padding: 13px; border-bottom: 1px solid var(--color-border-subtle); }
.task-list-pane > header > div { display: flex; justify-content: space-between; color: var(--color-text-strong); font-size: 13px; }
.task-list-pane > header small { color: var(--color-text-muted); font-size: 10px; }
.task-list-pane :deep(.el-segmented) { width: 100%; }
.virtual-scroll { position: relative; flex: 1; min-height: 0; overflow: auto; padding: 7px; }
.virtual-list { position: relative; width: 100%; }
.task-row {
  position: absolute; inset-inline: 0; top: 0; display: flex; width: 100%; align-items: center;
  justify-content: space-between; gap: 8px; padding: 9px 10px; border: 0; border-left: 3px solid transparent;
  border-radius: 8px; background: transparent; color: var(--color-text); text-align: left; cursor: pointer;
}
.task-row:hover { background: var(--color-bg-hover); }
.task-row.active { border-left-color: var(--color-primary); background: var(--color-primary-soft); }
.task-copy { display: grid; min-width: 0; gap: 4px; }
.task-copy strong { overflow: hidden; color: var(--color-text-strong); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.task-copy small { overflow: hidden; color: var(--color-text-muted); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.task-detail { min-width: 0; min-height: 0; overflow: auto; padding: 20px 22px 28px; background: var(--color-bg-page); }
.detail-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 14px; }
.detail-head small { color: var(--color-text-muted); font-size: 10px; }
.detail-head h2 { margin: 3px 0; color: var(--color-text-strong); font-size: 19px; }
.detail-head p, .failure-card p, .warning-card p { margin: 0; color: var(--color-text-muted); font-size: 11px; line-height: 1.6; }
.failure-card { display: grid; gap: 5px; margin-top: 16px; padding: 12px; border: 1px solid var(--color-alert-danger-border); border-radius: 9px; background: var(--color-alert-danger-bg); }
.failure-card strong { color: var(--color-danger); font-size: 11px; }
.warning-card { display: grid; gap: 5px; margin-top: 16px; padding: 12px; border: 1px solid var(--color-alert-warning-border, #e6c20055); border-radius: 9px; background: var(--color-alert-warning-bg, #fff8e1); }
.warning-card strong { color: var(--color-warning, #b38600); font-size: 11px; }
.task-metadata { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1px; margin: 16px 0; overflow: hidden; border: 1px solid var(--color-border); border-radius: 9px; background: var(--color-border); }
.task-metadata > div { display: grid; gap: 4px; padding: 10px 12px; background: var(--color-bg-surface); }
.task-metadata dt { color: var(--color-text-muted); font-size: 9px; }
.task-metadata dd { margin: 0; color: var(--color-text-strong); font-size: 11px; }
.task-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.timeline-section, .task-log-section { margin-top: 22px; }
.section-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.section-head h3 { margin: 0; color: var(--color-text-strong); font-size: 13px; }
.section-head span { color: var(--color-text-muted); font-size: 10px; }
.event-timeline { display: grid; gap: 0; margin: 0; padding: 0; list-style: none; }
.event-timeline li { display: grid; grid-template-columns: 12px minmax(0, 1fr); gap: 8px; min-height: 54px; }
.event-timeline li:not(:last-child) .event-dot::after { content: ''; position: absolute; top: 10px; bottom: -45px; left: 4px; width: 1px; background: var(--color-border); }
.event-dot { position: relative; width: 9px; height: 9px; margin-top: 3px; border: 2px solid var(--color-primary); border-radius: 50%; background: var(--color-bg-page); }
.event-timeline strong { color: var(--color-text-strong); font-size: 11px; }
.event-timeline p { margin: 3px 0; color: var(--color-text-muted); font-size: 10px; }
.event-timeline time { color: var(--color-text-subtle); font-size: 9px; }
.task-log-list { display: grid; gap: 5px; margin: 0; padding: 0; list-style: none; }
.task-log-list li { display: grid; grid-template-columns: 70px 92px minmax(0, 1fr); gap: 8px; padding: 7px 9px; border-radius: 7px; background: var(--color-bg-surface); color: var(--color-text); font-size: 10px; }
.task-log-list li.error { border-left: 3px solid var(--color-danger); }
.task-log-list li.warning { border-left: 3px solid var(--color-warning); }
.task-log-list time { color: var(--color-text-subtle); }
.task-log-list strong { color: var(--color-text-muted); }
.empty-copy { color: var(--color-text-muted); font-size: 11px; }
@media (max-width: 900px) { .task-workspace { grid-template-columns: minmax(220px, 40%) minmax(0, 1fr); } .task-detail { padding: 16px; } }
</style>
