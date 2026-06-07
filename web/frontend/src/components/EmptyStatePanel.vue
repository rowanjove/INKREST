<script setup lang="ts">
import type { Component } from 'vue'

export type EmptyStateAction = {
  label: string
  type?: 'primary' | 'default' | 'warning' | 'success'
  plain?: boolean
  icon?: Component
  onClick: () => void
}

defineProps<{
  icon?: Component
  title: string
  description?: string
  actions?: EmptyStateAction[]
}>()
</script>

<template>
  <div class="empty-state-panel">
    <el-icon v-if="icon" class="empty-state-panel__icon" :size="48">
      <component :is="icon" />
    </el-icon>
    <h3 class="empty-state-panel__title">{{ title }}</h3>
    <p v-if="description" class="empty-state-panel__desc">{{ description }}</p>
    <div v-if="actions?.length" class="empty-state-panel__actions">
      <el-button
        v-for="(action, idx) in actions"
        :key="idx"
        :type="action.type || 'default'"
        :plain="action.plain"
        :icon="action.icon"
        @click="action.onClick"
      >
        {{ action.label }}
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.empty-state-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 40px 24px;
  text-align: center;
  color: var(--color-text-muted);
}

.empty-state-panel__icon {
  color: var(--color-text-subtle);
}

.empty-state-panel__title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text-strong);
}

.empty-state-panel__desc {
  margin: 0;
  max-width: 420px;
  font-size: 13px;
  line-height: 1.55;
  color: var(--color-text-muted);
}

.empty-state-panel__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
  margin-top: 6px;
}
</style>