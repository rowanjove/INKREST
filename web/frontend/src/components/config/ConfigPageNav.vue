<script setup lang="ts">
import type { ConfigSection } from '../../utils/configSections'

defineProps<{
  sections: ConfigSection[]
  onScrollTo: (id: string) => void
}>()
</script>

<template>
  <nav class="config-nav" aria-label="设置分区">
    <button
      v-for="item in sections"
      :key="item.id"
      type="button"
      class="nav-chip"
      @click="onScrollTo(item.id)"
    >
      {{ item.label }}
    </button>
  </nav>
</template>

<style scoped>
.config-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.nav-chip {
  padding: 6px 14px;
  border: 1px solid var(--color-border);
  border-radius: 999px;
  background: var(--color-bg-surface);
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-muted);
  cursor: pointer;
  transition: all 0.2s;
}

.nav-chip:hover {
  border-color: var(--primary, #c66f4f);
  color: var(--primary, #c66f4f);
  background: var(--color-primary-soft);
}
</style>