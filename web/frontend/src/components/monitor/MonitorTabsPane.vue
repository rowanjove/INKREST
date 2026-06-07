<script setup lang="ts">
import { Connection, Cpu, Document } from '@element-plus/icons-vue'
import LogStream from '../LogStream.vue'
import LLMLogViewer from '../LLMLogViewer.vue'
import TaskLog from '../TaskLog.vue'
import AutopilotRoundsPanel from '../AutopilotRoundsPanel.vue'
import CostSummaryPanel from '../CostSummaryPanel.vue'

const activeTab = defineModel<string>('activeTab', { required: true })
</script>

<template>
  <div class="tabs-container panel">
    <el-tabs v-model="activeTab" class="custom-tabs">
      <el-tab-pane name="task_logs">
        <template #label>
          <span class="tab-label-custom">
            <el-icon><Document /></el-icon>
            <span>任务流水日志</span>
          </span>
        </template>
        <div class="tab-content-wrapper full-height-pane task-rounds-split">
          <AutopilotRoundsPanel class="task-rounds-split__rounds" />
          <TaskLog class="task-rounds-split__logs" />
        </div>
      </el-tab-pane>

      <el-tab-pane name="agent_logs" lazy>
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

      <el-tab-pane name="logs" lazy>
        <template #label>
          <span class="tab-label-custom">
            <el-icon><Connection /></el-icon>
            <span>费用与接口</span>
          </span>
        </template>
        <div class="tab-content-wrapper full-height-pane cost-api-pane">
          <CostSummaryPanel compact hide-recent-rounds />
          <LLMLogViewer class="cost-api-pane__logs" />
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
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

.task-rounds-split {
  display: grid;
  grid-template-columns: minmax(240px, 320px) minmax(0, 1fr);
  gap: 16px;
  align-items: stretch;
}

.task-rounds-split__rounds,
.task-rounds-split__logs {
  min-height: 0;
  height: 100%;
}

.cost-api-pane {
  gap: 12px;
}

.cost-api-pane__logs {
  flex: 1;
  min-height: 0;
}

@media (max-width: 900px) {
  .task-rounds-split {
    grid-template-columns: 1fr;
    grid-template-rows: minmax(160px, 220px) minmax(0, 1fr);
  }
}
</style>