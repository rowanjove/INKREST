<script setup lang="ts">
import type { OutlineQueueStatus } from '../../entities/outline/outlineQueueStatus'
import { queueTone } from '../../utils/overviewProgress'

defineProps<{
  queue: OutlineQueueStatus | null
  loading: boolean
  error: string
  planningEntityCount: number
  onRetry: () => void
  onOpenDetails: () => void
  onOpenOutline: () => void
}>()
</script>

<template>
  <article class="summary-card queue-card" :class="`tone-${queueTone(queue)}`">
    <div class="card-heading">
      <span>卷计划</span>
      <span v-if="queue?.arc_queue_stale?.stale" class="status-text">待同步</span>
      <span v-else-if="queue" class="status-text">已加载</span>
    </div>
    <template v-if="queue">
      <strong>{{ queue.pending_briefs ?? 0 }}<small> 章待写</small></strong>
      <p class="queue-copy">
        {{ queue.current_macro_arc?.name || '尚未定位当前宏观卷' }}
        · 已写至 {{ queue.last_written_chapter ?? 0 }} 章
        · 规划窗口 {{ queue.planning_window ?? '—' }} 章
      </p>
      <div class="queue-actions">
        <button type="button" @click="onOpenDetails">查看详情</button>
        <button type="button" @click="onOpenOutline">打开策划</button>
      </div>
    </template>
    <template v-else-if="loading">
      <strong class="loading-text">读取中…</strong>
      <p class="queue-copy">正在读取卷队列。</p>
    </template>
    <template v-else>
      <strong class="loading-text">暂不可用</strong>
      <p class="queue-copy">{{ error || '卷计划暂时无法读取。' }}</p>
      <button type="button" class="retry-button" @click="onRetry">重试</button>
    </template>
    <p class="entity-meta">策划实体 {{ planningEntityCount }} 项</p>
  </article>
</template>

<style scoped>
.summary-card { min-width: 0; padding: var(--space-5); border: 1px solid var(--color-border); border-radius: var(--radius-lg); background: var(--color-bg-surface); box-shadow: var(--shadow-sm); }
.card-heading { display: flex; align-items: center; justify-content: space-between; gap: 8px; color: var(--color-text-muted); font-size: 12px; }
.status-text { color: var(--color-warning); font-size: 11px; }
.summary-card > strong { display: block; margin: var(--space-4) 0 5px; color: var(--color-text-strong); font-size: 30px; }
.summary-card strong small { color: var(--color-text-muted); font-size: 13px; font-weight: 500; }
.loading-text { font-size: 22px !important; }
.queue-copy, .entity-meta { margin: 0; color: var(--color-text-muted); font-size: 11px; line-height: 1.55; overflow-wrap: anywhere; }
.queue-actions { display: flex; gap: 10px; margin-top: 10px; }
.queue-actions button, .retry-button { padding: 0; border: 0; background: transparent; color: var(--color-primary); font: inherit; font-size: 11px; cursor: pointer; }
.queue-actions button:hover, .retry-button:hover { text-decoration: underline; }
.entity-meta { margin-top: 10px; color: var(--color-text-subtle); }
.tone-warning { border-color: color-mix(in srgb, var(--color-warning) 38%, var(--color-border)); }
.tone-danger { border-color: color-mix(in srgb, var(--color-danger) 38%, var(--color-border)); }
</style>

