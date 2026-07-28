<script setup lang="ts">
import { computed } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { useRoute } from 'vue-router'

import { useProjectStore } from '../../stores/project'

defineEmits<{ openCommand: [] }>()

const route = useRoute()
const projectStore = useProjectStore()
const title = computed(() => route.meta.title || '栖墨')
</script>

<template>
  <header class="app-topbar">
    <div class="breadcrumbs" aria-label="当前位置">
      <span v-if="projectStore.currentProject?.name">
        {{ projectStore.currentProject.name }}
      </span>
      <i v-if="projectStore.currentProject?.name" aria-hidden="true">/</i>
      <strong>{{ title }}</strong>
    </div>
    <button
      type="button"
      class="command-trigger"
      aria-label="打开全局搜索与命令面板"
      @click="$emit('openCommand')"
    >
      <el-icon><Search /></el-icon>
      <span>搜索或执行命令</span>
      <kbd>Ctrl K</kbd>
    </button>
  </header>
</template>

<style scoped>
.app-topbar {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 0 28px;
  border-bottom: 1px solid var(--color-border-subtle);
  background: color-mix(in srgb, var(--color-bg-surface) 92%, transparent);
  backdrop-filter: blur(14px);
}

.breadcrumbs {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--color-text-muted);
  font-size: 13px;
}

.breadcrumbs span,
.breadcrumbs strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.breadcrumbs i {
  color: var(--color-text-subtle);
  font-style: normal;
}

.breadcrumbs strong {
  color: var(--color-text-strong);
}

.command-trigger {
  min-width: 250px;
  height: 36px;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 0 10px;
  border: 1px solid var(--color-border);
  border-radius: 9px;
  background: var(--color-bg-surface-muted);
  color: var(--color-text-muted);
  cursor: pointer;
}

.command-trigger:hover {
  border-color: var(--color-primary);
  color: var(--color-text-strong);
}

.command-trigger kbd {
  margin-left: auto;
  padding: 2px 6px;
  border: 1px solid var(--color-border);
  border-radius: 5px;
  background: var(--color-bg-surface);
  color: var(--color-text-subtle);
  font: inherit;
  font-size: 11px;
}
</style>
