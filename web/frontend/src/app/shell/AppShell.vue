<script setup lang="ts">
import { defineAsyncComponent, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { useProjectStore } from '../../stores/project'
import { useProjectSnapshotStore } from '../../stores/projectSnapshot'
import type { BackendStatus } from '../bootstrap/useDesktopLifecycle'
import { useCommandPalette } from '../commands/useCommandPalette'
import AppSidebar from './AppSidebar.vue'
import AppTopbar from './AppTopbar.vue'

const CommandPalette = defineAsyncComponent(() => import('../commands/CommandPalette.vue'))
const DiagnosticsDrawer = defineAsyncComponent(
  () => import('../diagnostics/DiagnosticsDrawer.vue'),
)

const props = defineProps<{
  backendStatus: BackendStatus
  backendUnreachable: boolean
}>()

const route = useRoute()
const projectStore = useProjectStore()
const snapshotStore = useProjectSnapshotStore()
const diagnosticsRequested = ref(false)
const { isOpen: commandOpen, open: openCommand } = useCommandPalette()
let refreshTimer: number | null = null

const refreshSnapshot = () => {
  const projectId = projectStore.currentProject?.id
  if (projectId && props.backendStatus === 'online') {
    void snapshotStore.refresh(projectId, { force: true })
  }
}

watch(
  () => projectStore.currentProject?.id,
  (projectId) => {
    snapshotStore.invalidate(projectId || null)
    if (projectId) void snapshotStore.refresh(projectId)
  },
  { immediate: true },
)

onMounted(() => {
  refreshTimer = window.setInterval(refreshSnapshot, 15_000)
  window.addEventListener('inkrest-pipeline-started', refreshSnapshot)
  window.addEventListener('inkrest-batch-finished', refreshSnapshot)
})

onBeforeUnmount(() => {
  if (refreshTimer !== null) window.clearInterval(refreshTimer)
  window.removeEventListener('inkrest-pipeline-started', refreshSnapshot)
  window.removeEventListener('inkrest-batch-finished', refreshSnapshot)
})
</script>

<template>
  <div class="app-shell">
    <el-alert
      v-if="backendStatus !== 'restarting' && (backendStatus === 'offline' || backendUnreachable)"
      class="backend-offline-alert"
      type="error"
      :closable="false"
      show-icon
      title="栖墨后台未响应"
      description="请重启应用或检查本地服务端口；连接恢复后提示会自动消失。"
    />
    <AppSidebar
      :backend-status="backendStatus"
      :backend-unreachable="backendUnreachable"
      @open-diagnostics="diagnosticsRequested = true"
    />
    <section class="app-content">
      <AppTopbar @open-command="openCommand" />
      <main class="app-workspace" :class="{ 'app-workspace--full': route.meta.fullBleed }">
        <router-view />
      </main>
    </section>
    <CommandPalette v-if="commandOpen" v-model="commandOpen" />
    <DiagnosticsDrawer
      v-if="diagnosticsRequested"
      v-model="diagnosticsRequested"
      :backend-status="backendStatus"
      :backend-unreachable="backendUnreachable"
    />
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 236px minmax(0, 1fr);
  background: var(--color-bg-app);
}

.app-content {
  min-width: 0;
  height: 100vh;
  display: grid;
  grid-template-rows: 60px minmax(0, 1fr);
  overflow: hidden;
}

.app-workspace {
  min-width: 0;
  overflow: auto;
  padding: 28px 36px 40px;
}

.app-workspace--full {
  padding: 0;
  overflow: hidden;
}

.backend-offline-alert {
  position: fixed;
  top: 12px;
  left: 50%;
  z-index: 3000;
  width: min(560px, calc(100vw - 24px));
  transform: translateX(-50%);
  box-shadow: var(--shadow-panel);
}
</style>
