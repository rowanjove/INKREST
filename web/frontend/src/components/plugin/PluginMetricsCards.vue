<script setup lang="ts">
defineProps<{
  totalCount: number
  activeCount: number
}>()
</script>

<template>
  <div class="plugin-metrics">
    <div class="metric-card total-card">
      <span class="m-label">已装插件数</span>
      <span class="m-val">{{ totalCount }}</span>
    </div>
    <div class="metric-card active-card">
      <span class="m-label">启用运行中</span>
      <span class="m-val">{{ activeCount }}</span>
    </div>
  </div>
</template>

<style scoped>
.plugin-metrics {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.metric-card {
  background: var(--color-bg-surface);
  border-radius: 16px;
  padding: 22px 24px;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--border-light);
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.02);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 25px rgba(15, 23, 42, 0.06);
}

.total-card {
  background: linear-gradient(135deg, var(--color-bg-surface) 0%, var(--color-bg-surface-muted) 100%);
}

.active-card {
  background: linear-gradient(135deg, var(--color-bg-surface) 0%, #fff6f2 100%);
  border-color: rgba(198, 111, 79, 0.2);
}

.m-label {
  font-size: 13.5px;
  color: var(--text-muted);
  font-weight: 600;
}

.m-val {
  font-size: 34px;
  font-weight: 800;
  color: var(--text-main);
  margin-top: 6px;
}

.active-card .m-val {
  color: var(--primary);
}
</style>