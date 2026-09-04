<script setup lang="ts">
defineProps<{
  totalCount: number
  activeCount: number
}>()
</script>

<template>
  <div class="plugin-metrics">
    <span class="metric-pill total-pill">
      <span class="m-label">已装插件</span>
      <strong class="m-val">{{ totalCount }}</strong>
    </span>
    <span class="metric-pill active-pill" :class="{ 'has-active': activeCount > 0 }">
      <span class="m-dot" />
      <span class="m-label">启用运行中</span>
      <strong class="m-val">{{ activeCount }}</strong>
    </span>
  </div>
</template>

<style scoped>
.plugin-metrics {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  vertical-align: middle;
}

.metric-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 9999px;
  font-size: 12px;
  line-height: 1.4;
  border: 1px solid var(--border-light, #e2e8f0);
  background: var(--color-bg-surface-muted, #f8fafc);
  color: var(--text-muted, #64748b);
  transition: all 0.2s ease;
}

.metric-pill .m-label {
  font-weight: 500;
}

.metric-pill .m-val {
  font-weight: 700;
  color: var(--text-main, #0f172a);
}

.active-pill.has-active {
  background: #f0fdf4;
  border-color: #bbf7d0;
  color: #166534;
}

.active-pill.has-active .m-val {
  color: #15803d;
}

.m-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #94a3b8;
}

.active-pill.has-active .m-dot {
  background: #22c55e;
  box-shadow: 0 0 6px rgba(34, 197, 94, 0.4);
}
</style>