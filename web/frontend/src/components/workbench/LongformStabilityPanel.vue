<script setup lang="ts">
import type { FactoryRiskAction, FactoryStabilityReport } from '../../types/factory'

defineProps<{
  report: FactoryStabilityReport | null | undefined
  priority?: boolean
}>()

const emit = defineEmits<{
  action: [action: FactoryRiskAction]
}>()

function statusTone(status?: FactoryStabilityReport['status']) {
  if (status === 'stable') return 'success'
  if (status === 'blocked') return 'danger'
  if (status === 'warning') return 'warning'
  return 'info'
}

function primaryAction(report: FactoryStabilityReport | null | undefined) {
  return report?.next_actions?.[0] || null
}
</script>

<template>
  <section class="longform-stability-panel" :class="{ 'is-priority': priority }">
    <div class="risk-panel-head">
      <div>
        <p>长篇稳定雷达</p>
        <h3>{{ report?.score ?? 0 }} 分</h3>
      </div>
      <el-tag :type="statusTone(report?.status)" effect="plain">
        {{ report?.status || 'missing' }}
      </el-tag>
    </div>
    <p class="risk-summary">{{ report?.summary || '等待生产计划生成。' }}</p>
    <div class="tracked-grid">
      <span>角色 {{ report?.tracked.characters || 0 }}</span>
      <span>伏笔 {{ report?.tracked.foreshadows || 0 }}</span>
      <span>承诺 {{ report?.tracked.reader_promises || 0 }}</span>
      <span>秘密 {{ report?.tracked.secrets || 0 }}</span>
    </div>
    <article v-if="report?.risks?.length" class="top-risk">
      <div>
        <strong>{{ report.risks[0].label }}</strong>
        <span>{{ report.risks[0].detail }}</span>
      </div>
    </article>
    <el-button v-if="primaryAction(report)" size="small" plain @click="emit('action', primaryAction(report)!)">
      {{ primaryAction(report)!.label }}
    </el-button>
  </section>
</template>

<style scoped>
.longform-stability-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
  padding: 14px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-surface);
}

.longform-stability-panel.is-priority {
  border-color: var(--color-primary);
}

.risk-panel-head,
.top-risk {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.risk-panel-head p,
.risk-summary,
.top-risk span,
.tracked-grid span {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.45;
}

h3 {
  margin: 4px 0 0;
  font-size: 20px;
}

.tracked-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px;
}

.tracked-grid span,
.top-risk {
  padding: 8px;
  border-radius: 8px;
  background: var(--color-bg-surface-muted);
}

.top-risk {
  justify-content: flex-start;
}

.top-risk strong,
.top-risk span {
  display: block;
}

.top-risk strong {
  font-size: 13px;
}

@media (max-width: 760px) {
  .tracked-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>