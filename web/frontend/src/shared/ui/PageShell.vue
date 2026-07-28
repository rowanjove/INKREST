<script setup lang="ts">
defineProps<{
  title: string
  description?: string
  eyebrow?: string
  compact?: boolean
}>()
</script>

<template>
  <section class="ui-page-shell" :class="{ 'ui-page-shell--compact': compact }">
    <header class="ui-page-shell__header">
      <div class="ui-page-shell__copy">
        <p v-if="eyebrow" class="ui-page-shell__eyebrow">{{ eyebrow }}</p>
        <h1>{{ title }}</h1>
        <p v-if="description" class="ui-page-shell__description">{{ description }}</p>
      </div>
      <div v-if="$slots.actions" class="ui-page-shell__actions">
        <slot name="actions" />
      </div>
    </header>
    <div class="ui-page-shell__body">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.ui-page-shell {
  width: min(100%, var(--layout-content-max));
  margin-inline: auto;
}

.ui-page-shell--compact {
  width: min(100%, var(--layout-content-compact));
}

.ui-page-shell__header {
  min-height: 72px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-6);
  margin-bottom: var(--space-6);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border-subtle);
}

.ui-page-shell__copy { min-width: 0; }

.ui-page-shell__eyebrow {
  margin: 0 0 var(--space-1);
  color: var(--color-primary);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.ui-page-shell h1 {
  margin: 0;
  color: var(--color-text-strong);
  font-size: clamp(24px, 2.4vw, 32px);
  font-weight: 800;
  letter-spacing: -0.025em;
  line-height: 1.15;
}

.ui-page-shell__description {
  max-width: 720px;
  margin: var(--space-2) 0 0;
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 1.65;
}

.ui-page-shell__actions {
  display: flex;
  flex: none;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: var(--space-2);
}

.ui-page-shell__body { min-width: 0; }
</style>
