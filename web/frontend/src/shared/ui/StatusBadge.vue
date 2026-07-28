<script setup lang="ts">
withDefaults(defineProps<{
  label: string
  tone?: 'neutral' | 'info' | 'success' | 'warning' | 'danger'
  dot?: boolean
}>(), {
  tone: 'neutral',
  dot: false,
})
</script>

<template>
  <span class="ui-status-badge" :class="`ui-status-badge--${tone}`">
    <span v-if="dot" class="ui-status-badge__dot" aria-hidden="true" />
    {{ label }}
  </span>
</template>

<style scoped>
.ui-status-badge {
  min-height: 24px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 8px;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: var(--color-bg-surface-muted);
  color: var(--color-text-muted);
  font-size: 11px;
  font-weight: 650;
  line-height: 1.2;
}

.ui-status-badge__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.ui-status-badge--info {
  border-color: color-mix(in srgb, var(--color-info) 28%, transparent);
  background: var(--color-info-soft);
  color: var(--color-info);
}

.ui-status-badge--success {
  border-color: color-mix(in srgb, var(--color-success) 28%, transparent);
  background: var(--color-success-soft);
  color: var(--color-success);
}

.ui-status-badge--warning {
  border-color: color-mix(in srgb, var(--color-warning) 28%, transparent);
  background: var(--color-warning-soft);
  color: var(--color-warning);
}

.ui-status-badge--danger {
  border-color: color-mix(in srgb, var(--color-danger) 28%, transparent);
  background: var(--color-danger-soft);
  color: var(--color-danger);
}
</style>
