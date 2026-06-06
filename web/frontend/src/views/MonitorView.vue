<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Loading, Connection, Document, Cpu } from '@element-plus/icons-vue'
import BatchRunStatusBanner from '../components/BatchRunStatusBanner.vue'
import NovelBatchRunDialog from '../components/NovelBatchRunDialog.vue'
import { useTasksStore } from '../stores/tasks'
import LogStream from '../components/LogStream.vue'
import LLMLogViewer from '../components/LLMLogViewer.vue'
import TaskLog from '../components/TaskLog.vue'

const route = useRoute()
const router = useRouter()
const tasksStore = useTasksStore()
const { isRunning, currentChapterId, lastTaskFailure } = storeToRefs(tasksStore)

const activeTab = ref('task_logs')

const syncTab = () => {
  if (route.query.tab === 'tasks') {
    router.replace('/chapters/maintenance')
    return
  }
  const allowedTabs = ['task_logs', 'agent_logs', 'logs']
  if (route.query.tab && allowedTabs.includes(route.query.tab as string)) {
    activeTab.value = route.query.tab as string
  }
}

watch(activeTab, (newTab) => {
  router.replace({ query: { ...route.query, tab: newTab } })
})

watch(() => route.query.tab, () => {
  syncTab()
})

onMounted(() => {
  tasksStore.connectElectronEvents()
  tasksStore.startPolling()
  tasksStore.startRuntimeLogPolling()
  syncTab()
})

onUnmounted(() => {
  tasksStore.stopPolling()
  tasksStore.stopRuntimeLogPolling()
})

function dismissTaskFailure() {
  lastTaskFailure.value = null
}
</script>

<template>
  <div class="monitor-view-page">
    <header class="page-head">
      <div class="page-title-area">
        <h1>日志中心</h1>
        <p>查看任务流水、Agent 实时日志与接口调用记录；修章与待处理见「章节 → 章节维护」。</p>
      </div>
      <div class="running-badge" v-if="isRunning">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>正在生成章节 {{ currentChapterId }}</span>
      </div>
    </header>

    <BatchRunStatusBanner />
    <el-alert
      v-if="lastTaskFailure"
      type="error"
      :closable="true"
      show-icon
      class="task-failure-alert"
      :title="lastTaskFailure.code ? `[${lastTaskFailure.code}] 任务失败` : '任务失败'"
      :description="lastTaskFailure.hint"
      @close="dismissTaskFailure"
    />
    <NovelBatchRunDialog />

    <div class="tabs-container panel">
      <el-tabs v-model="activeTab" class="custom-tabs">
        <el-tab-pane name="task_logs">
          <template #label>
            <span class="tab-label-custom">
              <el-icon><Document /></el-icon>
              <span>任务流水日志</span>
            </span>
          </template>
          <div class="tab-content-wrapper full-height-pane">
            <TaskLog />
          </div>
        </el-tab-pane>

        <el-tab-pane name="agent_logs">
          <template #label>
            <span class="tab-label-custom">
              <el-icon><Cpu /></el-icon>
              <span>Agent 实时日志</span>
            </span>
          </template>
          <div class="tab-content-wrapper full-height-pane">
            <LogStream />
          </div>
        </el-tab-pane>

        <el-tab-pane name="logs">
          <template #label>
            <span class="tab-label-custom">
              <el-icon><Connection /></el-icon>
              <span>接口调用日志</span>
            </span>
          </template>
          <div class="tab-content-wrapper full-height-pane">
            <LLMLogViewer />
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<style scoped>
.monitor-view-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-height: calc(100vh - 96px);
  height: calc(100vh - 96px);
  max-height: calc(100vh - 96px);
  overflow: hidden;
}

.running-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #fdf6ec;
  color: #e6a23c;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
}

.tabs-container {
  display: flex;
  flex: 1;
  min-height: 0;
  padding: 12px 18px 24px;
}

.custom-tabs {
  display: flex;
  flex: 1;
  min-height: 0;
  flex-direction: column;
}

.custom-tabs :deep(.el-tabs__content),
.custom-tabs :deep(.el-tab-pane) {
  display: flex;
  flex: 1;
  min-height: 0;
  flex-direction: column;
}

.tab-label-custom {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 15px;
  font-weight: 600;
}

.tab-content-wrapper {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  padding-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.full-height-pane {
  flex: 1;
  min-height: 0;
  height: 100%;
}

.full-height-pane :deep(.panel),
.full-height-pane :deep(.log-stream),
.full-height-pane :deep(.llm-log-card) {
  height: 100% !important;
  box-sizing: border-box;
}

.full-height-pane :deep(.el-card) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.full-height-pane :deep(.el-card__body) {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}
</style>