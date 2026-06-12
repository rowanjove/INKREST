<script setup lang="ts">
import { computed } from 'vue'
import { DocumentChecked } from '@element-plus/icons-vue'
import type { ProductionPlanSummary } from '../../types/factory'

const props = defineProps<{
  plan: ProductionPlanSummary | null | undefined
}>()

const readinessPercent = computed(() => {
  const readiness = props.plan?.readiness
  if (!readiness?.total) return 0
  return Math.round((readiness.ok / readiness.total) * 100)
})
</script>

<template>
  <section class="production-plan-panel">
    <div class="panel-head">
      <div>
        <p>生产计划</p>
        <h3>{{ plan?.title || '等待生成生产计划' }}</h3>
      </div>
      <el-tag :type="plan?.status === 'ready' ? 'success' : 'warning'" effect="plain">
        {{ plan?.status === 'ready' ? '可生产' : plan?.status === 'planning' ? '待完善' : '未生成' }}
      </el-tag>
    </div>

    <div class="plan-body">
      <div class="plan-progress">
        <el-icon><DocumentChecked /></el-icon>
        <div>
          <strong>{{ plan?.planned_chapters || 0 }} / {{ plan?.target_chapters || 0 }}</strong>
          <span>已规划 / 目标章节</span>
        </div>
      </div>
      <div class="readiness-box">
        <span>开书清单 {{ plan?.readiness.ok || 0 }} / {{ plan?.readiness.total || 0 }}</span>
        <el-progress :percentage="readinessPercent" :show-text="false" :stroke-width="7" />
      </div>
    </div>

    <div v-if="plan?.selling_points?.length" class="selling-points">
      <span v-for="point in plan.selling_points" :key="point">{{ point }}</span>
    </div>
    <div v-if="plan?.readiness.missing?.length" class="missing-list">
      <strong>待补齐</strong>
      <span>{{ plan.readiness.missing.join('、') }}</span>
    </div>
  </section>
</template>

<style scoped>
.production-plan-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-surface);
}

.panel-head,
.plan-body {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.panel-head p {
  margin: 0;
  font-size: 12px;
  color: var(--color-text-muted);
}

h3 {
  margin: 4px 0 0;
  font-size: 16px;
}

.plan-progress {
  display: flex;
  align-items: center;
  gap: 10px;
}

.plan-progress .el-icon {
  color: var(--color-primary);
  font-size: 22px;
}

.plan-progress strong,
.plan-progress span {
  display: block;
}

.plan-progress span,
.readiness-box span,
.missing-list {
  color: var(--color-text-muted);
  font-size: 12px;
}

.readiness-box {
  min-width: 180px;
}

.selling-points {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.selling-points span {
  padding: 4px 8px;
  border-radius: 999px;
  color: var(--color-primary);
  background: var(--color-primary-soft);
  font-size: 12px;
}

.missing-list {
  display: flex;
  gap: 6px;
}

@media (max-width: 820px) {
  .panel-head,
  .plan-body {
    align-items: stretch;
    flex-direction: column;
  }

  .readiness-box {
    min-width: 0;
  }
}
</style>
