<script setup lang="ts">
import { CircleCheck, Clock, Loading, Tools, Warning } from '@element-plus/icons-vue'
import type { FactoryPipelineStep, FactoryQualitySummary } from '../../types/factory'

defineProps<{
  steps: FactoryPipelineStep[]
  quality?: FactoryQualitySummary | null
}>()

function iconFor(state: FactoryPipelineStep['state']) {
  if (state === 'done') return CircleCheck
  if (state === 'active') return Loading
  if (state === 'blocked' || state === 'warning') return Warning
  return Clock
}

function qualityTone(status?: FactoryQualitySummary['status']) {
  if (status === 'blocked') return 'danger'
  if (status === 'passed') return 'success'
  return 'info'
}
</script>

<template>
  <section class="factory-pipeline-panel">
    <div class="panel-title">
      <el-icon><Tools /></el-icon>
      <h3>AI 工厂流水线</h3>
    </div>
    <div class="factory-step-grid">
      <article
        v-for="step in steps"
        :key="step.id"
        class="factory-step"
        :class="`state-${step.state}`"
      >
        <el-icon :class="{ 'is-loading': step.state === 'active' }">
          <component :is="iconFor(step.state)" />
        </el-icon>
        <strong>{{ step.label }}</strong>
      </article>
    </div>
    <div v-if="quality" class="quality-summary-strip">
      <div>
        <span>质检报告</span>
        <strong>{{ quality.passed }} / {{ quality.total_reports }}</strong>
      </div>
      <div>
        <span>未通过</span>
        <strong>{{ quality.failed }}</strong>
      </div>
      <div>
        <span>AI 味风险</span>
        <strong>{{ quality.ai_flavor_risks }}</strong>
      </div>
      <el-tag :type="qualityTone(quality.status)" effect="plain">
        {{ quality.status === 'blocked' ? '待修复' : quality.status === 'passed' ? '已通过' : '待质检' }}
      </el-tag>
      <p v-if="quality.latest_issue">
        最近问题：第 {{ quality.latest_issue.chapter_id }} 章 · {{ quality.latest_issue.blocked_by.join(' / ') || quality.latest_issue.ai_flavor_risk }}
      </p>
    </div>
  </section>
</template>

<style scoped>
.factory-pipeline-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-surface);
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

h3 {
  margin: 0;
  font-size: 16px;
}

.factory-step-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 8px;
}

.factory-step {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  min-height: 48px;
  padding: 8px;
  border-radius: 8px;
  background: var(--color-bg-surface-muted);
  color: var(--color-text-muted);
  text-align: center;
}

.factory-step.state-done {
  color: #15803d;
  background: #f0fdf4;
}

.factory-step.state-active {
  color: #1d4ed8;
  background: #eff6ff;
}

.factory-step.state-warning {
  color: #b45309;
  background: #fffbeb;
}

.factory-step.state-blocked {
  color: #b91c1c;
  background: #fef2f2;
}

.quality-summary-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr)) auto;
  gap: 8px;
  align-items: center;
  padding: 8px;
  border-radius: 8px;
  background: var(--color-bg-surface-muted);
}

.quality-summary-strip div {
  min-width: 0;
}

.quality-summary-strip span,
.quality-summary-strip p {
  color: var(--color-text-muted);
  font-size: 12px;
}

.quality-summary-strip span,
.quality-summary-strip strong {
  display: block;
}

.quality-summary-strip p {
  grid-column: 1 / -1;
  margin: 0;
  line-height: 1.45;
}

@media (max-width: 920px) {
  .factory-step-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .quality-summary-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .factory-step-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .quality-summary-strip {
    grid-template-columns: 1fr;
  }
}
</style>