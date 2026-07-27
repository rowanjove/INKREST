<script setup lang="ts">
defineProps<{
  title?: string
  description: string
  retryLabel?: string
}>()

defineEmits<{ retry: [] }>()
</script>

<template>
  <section class="ui-error-state" role="alert" aria-live="assertive">
    <span class="ui-error-state__mark" aria-hidden="true">!</span>
    <div class="ui-error-state__copy">
      <h2>{{ title || '暂时无法完成' }}</h2>
      <p>{{ description }}</p>
      <button v-if="retryLabel" type="button" @click="$emit('retry')">
        {{ retryLabel }}
      </button>
    </div>
  </section>
</template>

<style scoped>
.ui-error-state {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid color-mix(in srgb, var(--color-danger) 28%, transparent);
  border-radius: var(--radius-md);
  background: var(--color-danger-soft);
}

.ui-error-state__mark {
  width: 22px;
  height: 22px;
  display: grid;
  flex: none;
  place-items: center;
  border-radius: 50%;
  background: var(--color-danger);
  color: white;
  font-size: 12px;
  font-weight: 800;
}

.ui-error-state h2 {
  margin: 1px 0 0;
  color: var(--color-text-strong);
  font-size: 14px;
}

.ui-error-state p {
  margin: var(--space-1) 0 0;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.55;
}

.ui-error-state button {
  margin-top: var(--space-3);
  padding: 6px 10px;
  border: 1px solid var(--color-danger);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-danger);
  cursor: pointer;
  font-size: 12px;
  font-weight: 650;
}
</style>
