<script setup lang="ts">
withDefaults(defineProps<{
  title: string
  description: string
  eyebrow?: string
}>(), {
  eyebrow: '策划中心',
})
</script>

<template>
  <header class="planning-workspace-header">
    <div class="planning-workspace-copy">
      <p class="planning-eyebrow">{{ eyebrow }}</p>
      <h1>{{ title }}</h1>
      <p class="planning-description">{{ description }}</p>
    </div>
    <div v-if="$slots.meta || $slots.actions" class="planning-workspace-tools">
      <div v-if="$slots.meta" class="planning-workspace-meta">
        <slot name="meta" />
      </div>
      <div v-if="$slots.actions" class="planning-workspace-actions">
        <slot name="actions" />
      </div>
    </div>
  </header>
</template>

<style scoped>
.planning-workspace-header {
  min-height: 86px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-5);
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-surface);
}
.planning-workspace-copy { min-width: 0; }
.planning-eyebrow { margin: 0 0 3px; color: var(--color-primary); font-size: 11px; font-weight: 800; letter-spacing: .1em; }
.planning-workspace-header h1 { margin: 0; color: var(--color-text-strong); font-size: 22px; line-height: 1.25; }
.planning-description { margin: 5px 0 0; color: var(--color-text-muted); font-size: 12px; line-height: 1.5; }
.planning-workspace-tools { display: flex; align-items: center; justify-content: flex-end; gap: var(--space-3); }
.planning-workspace-meta,
.planning-workspace-actions { display: flex; align-items: center; justify-content: flex-end; gap: var(--space-3); }
.planning-workspace-meta { flex-wrap: wrap; }

@media (max-width: 900px) {
  .planning-workspace-header { align-items: stretch; flex-direction: column; }
  .planning-workspace-tools { justify-content: space-between; }
  .planning-workspace-meta { justify-content: flex-start; }
}
@media (max-width: 620px) {
  .planning-workspace-tools { align-items: stretch; flex-direction: column; }
  .planning-workspace-actions { justify-content: flex-start; flex-wrap: wrap; }
}
</style>
