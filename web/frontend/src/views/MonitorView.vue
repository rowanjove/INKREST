<script setup lang="ts">
import { Loading } from '@element-plus/icons-vue'
import BatchRunStatusBanner from '../components/BatchRunStatusBanner.vue'
import NovelBatchRunDialog from '../components/NovelBatchRunDialog.vue'
import MonitorTabsPane from '../components/monitor/MonitorTabsPane.vue'
import { useMonitorView } from '../composables/useMonitorView'

const { isRunning, currentChapterId, lastTaskFailure, activeTab, dismissTaskFailure } = useMonitorView()
</script>

<template>
  <div class="monitor-view-page">
    <header class="page-head">
      <div class="page-title-area">
        <h1>日志中心</h1>
        <p>查看任务流水与连写轮次、Agent 实时日志、费用摘要与接口调用；修章与待处理见「章节 → 章节维护」。</p>
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

    <MonitorTabsPane v-model:active-tab="activeTab" />
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
</style>