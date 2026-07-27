<script setup lang="ts">
defineProps<{
  title: string
  description?: string
  compact?: boolean
}>()
</script>

<template>
  <section
    class="ui-empty-state"
    :class="{ 'ui-empty-state--compact': compact }"
    role="status"
    aria-live="polite"
  >
    <div v-if="$slots.icon" class="ui-empty-state__icon" aria-hidden="true">
      <slot name="icon" />
    </div>
    <h2>{{ title }}</h2>
    <p v-if="description">{{ description }}</p>
    <div v-if="$slots.actions" class="ui-empty-state__actions">
      <slot name="actions" />
    </div>
  </section>
</template>

<style scoped>
.ui-empty-state {
  min-height: 280px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: var(--space-2);
  padding: var(--space-10) var(--space-6);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-surface-muted);
  text-align: center;
}

.ui-empty-state--compact {
  min-height: 180px;
  padding-block: var(--space-7);
}

.ui-empty-state__icon {
  display: grid;
  place-items: center;
  margin-bottom: var(--space-2);
  color: var(--color-text-subtle);
  font-size: 36px;
}

.ui-empty-state h2 {
  margin: 0;
  color: var(--color-text-strong);
  font-size: 17px;
  font-weight: 700;
}

.ui-empty-state p {
  max-width: 440px;
  margin: 0;
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 1.6;
}

.ui-empty-state__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--space-2);
  margin-top: var(--space-3);
}
</style>
