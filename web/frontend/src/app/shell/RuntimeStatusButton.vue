<script setup lang="ts">
import { computed } from 'vue'

import { useProjectSnapshotStore } from '../../stores/projectSnapshot'
import type { BackendStatus } from '../bootstrap/useDesktopLifecycle'

const props = defineProps<{
  backendStatus: BackendStatus
  backendUnreachable: boolean
}>()

defineEmits<{ open: [] }>()

const snapshotStore = useProjectSnapshotStore()

const tone = computed(() => {
  if (props.backendStatus !== 'online' || props.backendUnreachable) return 'danger'
  if (snapshotStore.status === 'loading' || snapshotStore.status === 'idle') return 'checking'
  if (snapshotStore.status === 'error') return 'danger'
  if (snapshotStore.snapshot?.blocking_issues.length) return 'warning'
  return 'ready'
})

const label = computed(() => {
  if (props.backendStatus === 'restarting') return '服务重启中'
  if (props.backendStatus !== 'online' || props.backendUnreachable) return '服务离线'
  if (snapshotStore.status === 'loading' || snapshotStore.status === 'idle') return '正在检查'
  if (snapshotStore.status === 'error') return '状态不可用'
  const snapshot = snapshotStore.snapshot
  if (!snapshot) return '等待项目'
  if (snapshot.active_tasks.length) return `${snapshot.active_tasks.length} 个任务进行中`
  if (snapshot.blocking_issues.length) return `${snapshot.blocking_issues.length} 项待处理`
  return '运行正常'
})
</script>

<template>
  <button
    type="button"
    class="runtime-status"
    :class="`runtime-status--${tone}`"
    :aria-label="`运行状态：${label}`"
    @click="$emit('open')"
  >
    <span class="runtime-status__dot" aria-hidden="true" />
    <span>
      <strong>运行状态</strong>
      <small>{{ label }}</small>
    </span>
  </button>
</template>

<style scoped>
.runtime-status {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.045);
  color: var(--color-text-sidebar);
  cursor: pointer;
  text-align: left;
}

.runtime-status:hover {
  border-color: rgba(198, 111, 79, 0.5);
  background: rgba(255, 255, 255, 0.075);
}

.runtime-status__dot {
  width: 9px;
  height: 9px;
  flex: none;
  border-radius: 50%;
  background: var(--color-success);
  box-shadow: 0 0 0 3px var(--color-success-soft);
}

.runtime-status--warning .runtime-status__dot {
  background: var(--color-warning);
  box-shadow: 0 0 0 3px var(--color-warning-soft);
}

.runtime-status--danger .runtime-status__dot {
  background: var(--color-danger);
  box-shadow: 0 0 0 3px var(--color-danger-soft);
}

.runtime-status--checking .runtime-status__dot {
  background: var(--color-text-sidebar-muted);
  box-shadow: 0 0 0 3px rgba(167, 179, 196, 0.2);
  animation: status-pulse 1.2s ease-in-out infinite;
}

.runtime-status strong,
.runtime-status small {
  display: block;
}

.runtime-status strong {
  font-size: 12px;
}

.runtime-status small {
  max-width: 168px;
  margin-top: 2px;
  overflow: hidden;
  color: var(--color-text-sidebar-dim);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@keyframes status-pulse {
  50% { opacity: 0.45; }
}
</style>
