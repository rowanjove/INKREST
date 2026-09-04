<script setup lang="ts">
import { computed } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { useRoute, useRouter } from 'vue-router'

import { useProjectStore } from '../../stores/project'
import { useProjectSnapshotStore } from '../../stores/projectSnapshot'
import {
  firstEnabledSnapshotAction,
  resolveSnapshotActionLocation,
} from './workflowActions'

defineEmits<{ openCommand: [] }>()

const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()
const snapshotStore = useProjectSnapshotStore()
const title = computed(() => route.meta.title || '栖墨')
const nextAction = computed(() =>
  firstEnabledSnapshotAction(snapshotStore.snapshot?.next_actions || []),
)

function openNextAction() {
  if (!nextAction.value) return
  void router.push(resolveSnapshotActionLocation(nextAction.value))
}
</script>

<template>
  <header class="app-topbar">
    <div class="breadcrumbs" aria-label="当前位置">
      <template v-if="route.meta.scope === 'project' && projectStore.currentProject?.name">
        <button
          type="button"
          class="breadcrumb-link"
          title="返回书库"
          @click="router.push('/')"
        >
          书库
        </button>
        <i aria-hidden="true">/</i>
        <span>{{ projectStore.currentProject.name }}</span>
        <i aria-hidden="true">/</i>
      </template>
      <strong>{{ title }}</strong>
    </div>
    <div
      v-if="route.meta.scope === 'project' && projectStore.currentProject?.id"
      class="next-action-slot"
      data-tour="next-action"
    >
      <button
        v-if="nextAction"
        type="button"
        class="next-action"
        :title="nextAction.reason || '打开建议步骤'"
        @click="openNextAction"
      >
        <span><small>首选下一步</small>{{ nextAction.label }}</span>
        <i aria-hidden="true">→</i>
      </button>
      <span v-else class="next-action-empty">
        {{ snapshotStore.status === 'loading' ? '正在判断下一步…' : '当前没有待办建议' }}
      </span>
    </div>
    <button
      type="button"
      class="command-trigger"
      data-tour="command-palette"
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

.breadcrumb-link {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  font-size: 13px;
  font-family: inherit;
  transition: color var(--motion-fast) var(--ease-standard);
}

.breadcrumb-link:hover {
  color: var(--color-brand-ink);
  text-decoration: underline;
}

.next-action-slot {
  min-width: 0;
  margin-left: auto;
}

.next-action {
  max-width: 250px;
  min-height: 38px;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 5px 10px 5px 12px;
  border: 1px solid color-mix(in srgb, var(--color-primary) 38%, var(--color-border));
  border-radius: 9px;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  cursor: pointer;
  text-align: left;
}

.next-action:hover {
  border-color: var(--color-primary);
}

.next-action > span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
  font-weight: 700;
}

.next-action small {
  display: block;
  color: var(--color-text-muted);
  font-size: 11px;
  font-weight: 600;
  line-height: 1.2;
}

.next-action i {
  font-style: normal;
  font-size: 13px;
}

.next-action-empty {
  color: var(--color-text-subtle);
  font-size: 12px;
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

@media (max-width: 1200px) {
  .app-topbar { padding-inline: 18px; gap: 12px; }
  .command-trigger { min-width: 112px; width: 112px; }
  .command-trigger > span { display: none; }
  .next-action { max-width: 190px; }
}
</style>
