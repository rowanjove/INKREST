<script setup lang="ts">
import { computed } from 'vue'
import type { ProductionWorkspace } from '../../entities/production/production'
import StatusBadge from '../../shared/ui/StatusBadge.vue'

const props = defineProps<{ workspace: ProductionWorkspace }>()

const completed = computed(
  () => Number(props.workspace.snapshot.chapter_progress.authoritative_completed || 0),
)
const target = computed(
  () => Number(props.workspace.snapshot.outline_progress.target_chapters || 0),
)
const progress = computed(() =>
  target.value ? Math.min(100, Math.round((completed.value / target.value) * 100)) : 0,
)
const active = computed(
  () =>
    props.workspace.tasks.filter((task) =>
      ['claimed', 'running'].includes(task.status),
    ).length,
)
const queued = computed(
  () => props.workspace.tasks.filter((task) => task.status === 'pending').length,
)
const qualityTone = computed(() =>
  props.workspace.reviews.summary.open_items ? 'danger' : 'success',
)
const cost = computed(
  () => Number(props.workspace.snapshot.cost_summary.persisted.total_cost_cny || 0),
)
</script>

<template>
  <section class="production-summary" aria-label="生产摘要">
    <article>
      <div class="summary-label"><span>正文进度</span><strong>{{ progress }}%</strong></div>
      <p><b>{{ completed }}</b> / {{ target || '—' }} 章已完成</p>
      <el-progress :percentage="progress" :show-text="false" />
    </article>
    <article>
      <div class="summary-label">
        <span>任务队列</span>
        <StatusBadge
          :label="active ? '运行中' : queued ? '等待中' : '空闲'"
          :tone="active ? 'info' : queued ? 'warning' : 'success'"
          dot
        />
      </div>
      <p><b>{{ active }}</b> 个运行 · {{ queued }} 个等待</p>
    </article>
    <article>
      <div class="summary-label">
        <span>审校修复</span>
        <StatusBadge
          :label="workspace.reviews.summary.open_items ? '有阻断' : '已通过'"
          :tone="qualityTone"
          dot
        />
      </div>
      <p>
        <b>{{ workspace.reviews.summary.open_items }}</b> 章待处理 ·
        {{ workspace.snapshot.quality_summary.passed }} 份通过
      </p>
    </article>
    <article>
      <div class="summary-label"><span>累计费用</span><strong>¥{{ cost.toFixed(2) }}</strong></div>
      <p>
        {{ workspace.snapshot.cost_summary.persisted.call_count || 0 }} 次调用 ·
        {{ workspace.snapshot.cost_summary.persisted.total_tokens || 0 }} tokens
      </p>
    </article>
  </section>
</template>

<style scoped>
.production-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-surface);
  box-shadow: var(--shadow-sm);
}
.production-summary article {
  min-width: 0;
  padding: 14px 16px;
  border-right: 1px solid var(--color-border-subtle);
}
.production-summary article:last-child { border-right: 0; }
.summary-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  color: var(--color-text-muted);
  font-size: 11px;
}
.summary-label strong { color: var(--color-text-strong); font-size: 13px; }
p { margin: 10px 0 0; color: var(--color-text-muted); font-size: 11px; }
p b { color: var(--color-text-strong); font-size: 17px; }
:deep(.el-progress) { margin-top: 7px; }
@media (max-width: 1100px) {
  .production-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .production-summary article:nth-child(2) { border-right: 0; }
  .production-summary article:nth-child(-n + 2) { border-bottom: 1px solid var(--color-border-subtle); }
}
</style>
