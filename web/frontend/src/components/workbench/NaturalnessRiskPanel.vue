<script setup lang="ts">
import { MagicStick } from '@element-plus/icons-vue'
import type { FactoryNaturalnessReport, FactoryRiskAction } from '../../types/factory'

defineProps<{
  report: FactoryNaturalnessReport | null | undefined
  priority?: boolean
}>()

const emit = defineEmits<{
  action: [action: FactoryRiskAction]
}>()

function statusTone(status?: FactoryNaturalnessReport['status']) {
  if (status === 'natural') return 'success'
  if (status === 'blocked') return 'danger'
  if (status === 'warning') return 'warning'
  return 'info'
}

function primaryAction(report: FactoryNaturalnessReport | null | undefined) {
  return report?.next_actions?.[0] || null
}
</script>

<template>
  <section class="naturalness-risk-panel" :class="{ 'is-priority': priority }">
    <div class="risk-panel-head">
      <div>
        <p>AI 味 / 平台风险</p>
        <h3>{{ report?.score ?? 0 }} 分</h3>
      </div>
      <el-tag :type="statusTone(report?.status)" effect="plain">
        {{ report?.status || 'missing' }}
      </el-tag>
    </div>
    <p class="risk-summary">{{ report?.summary || '等待质检报告生成。' }}</p>
    <div class="risk-type-row">
      <span v-for="item in report?.risk_types || []" :key="item.id">{{ item.label }} {{ item.count }}</span>
      <span v-if="!report?.risk_types?.length">暂无可见风险</span>
    </div>
    <article v-if="report?.sample_issues?.length" class="top-risk">
      <el-icon><MagicStick /></el-icon>
      <div>
        <strong>第 {{ report.sample_issues[0].chapter_id }} 章</strong>
        <span>{{ report.sample_issues[0].detail }}</span>
      </div>
    </article>
    <el-button v-if="primaryAction(report)" size="small" plain @click="emit('action', primaryAction(report)!)">
      {{ primaryAction(report)!.label }}
    </el-button>
  </section>
</template>

<style scoped>
.naturalness-risk-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
  padding: 14px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-surface);
}

.naturalness-risk-panel.is-priority {
  border-color: var(--color-warning);
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
.risk-type-row span {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.45;
}

h3 {
  margin: 4px 0 0;
  font-size: 20px;
}

.risk-type-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.risk-type-row span,
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
</style>
