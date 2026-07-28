<script setup lang="ts">
defineProps<{
  id: string
  eyebrow: string
  title: string
  description: string
}>()
</script>

<template>
  <section :id="id" class="config-task-group">
    <header class="task-group-head">
      <span>{{ eyebrow }}</span>
      <div>
        <h2>{{ title }}</h2>
        <p>{{ description }}</p>
      </div>
    </header>
    <div class="task-group-body">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.config-task-group {
  display: grid;
  gap: 12px;
  scroll-margin-top: 16px;
}
.task-group-head {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  align-items: start;
  gap: 12px;
  padding: 2px 4px;
}
.task-group-head > span {
  min-width: 58px;
  padding-top: 5px;
  color: var(--color-primary);
  font-size: 10px;
  font-weight: 850;
  letter-spacing: .12em;
  text-transform: uppercase;
}
.task-group-head h2 {
  margin: 0;
  color: var(--color-text-strong);
  font-size: 20px;
  line-height: 1.3;
}
.task-group-head p {
  margin: 4px 0 0;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.6;
}
.task-group-body {
  display: grid;
  gap: 10px;
  padding: 12px;
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-xl);
  background: color-mix(in srgb, var(--color-bg-surface-muted) 72%, transparent);
}
.task-group-body :deep(.fold-card),
.task-group-body :deep(.panel) {
  margin: 0 !important;
  border-color: var(--color-border);
  background: var(--color-bg-surface);
}
@media (max-width: 720px) {
  .task-group-head { grid-template-columns: 1fr; gap: 2px; }
  .task-group-head > span { padding-top: 0; }
  .task-group-body { padding: 8px; }
}
</style>
