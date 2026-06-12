<script setup lang="ts">
import { computed } from 'vue'
import { Cpu, Refresh, Tools } from '@element-plus/icons-vue'
import type { FactoryDashboard, FactoryMode } from '../../types/factory'
import {
  factoryModeOptions,
  formatFactoryState,
  getFactoryPrimaryAction,
  getFactoryTone,
} from '../../utils/factoryStatus'

const props = defineProps<{
  dashboard: FactoryDashboard | null
  loading?: boolean
  savingMode?: boolean
  error?: string
}>()

const emit = defineEmits<{
  action: [intent: string]
  refresh: []
  modeChange: [mode: FactoryMode]
}>()

const action = computed(() => props.dashboard ? getFactoryPrimaryAction(props.dashboard) : null)
const stateLabel = computed(() =>
  props.dashboard ? formatFactoryState(props.dashboard.factory_status.state) : '等待加载',
)
const tone = computed(() =>
  props.dashboard ? getFactoryTone(props.dashboard.factory_status.risk_level) : 'success',
)
const modeOptions = factoryModeOptions()
const progressPercent = computed(() => {
  const status = props.dashboard?.factory_status
  if (!status?.target_chapters) return 0
  return Math.min(100, Math.round((status.completed_chapters / status.target_chapters) * 100))
})
</script>

<template>
  <section class="factory-control-panel">
    <div class="factory-identity">
      <div class="factory-icon">
        <el-icon><Cpu /></el-icon>
      </div>
      <div class="factory-title-block">
        <p class="factory-kicker">生产模式</p>
        <h2>{{ dashboard?.project.name || 'AI 网文生产工厂' }}</h2>
        <el-select
          class="factory-mode-select"
          :model-value="dashboard?.project.mode"
          :disabled="!dashboard || savingMode"
          :loading="savingMode"
          size="small"
          @change="(mode: FactoryMode) => emit('modeChange', mode)"
        >
          <el-option
            v-for="option in modeOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
      </div>
    </div>

    <div class="factory-status-grid">
      <div class="factory-stat">
        <span>生产状态</span>
        <strong>{{ stateLabel }}</strong>
      </div>
      <div class="factory-stat">
        <span>章节进度</span>
        <strong>{{ dashboard?.factory_status.completed_chapters || 0 }} / {{ dashboard?.factory_status.target_chapters || 0 }}</strong>
      </div>
      <div class="factory-stat">
        <span>风险</span>
        <el-tag :type="tone" effect="plain">{{ dashboard?.factory_status.risk_level || 'low' }}</el-tag>
      </div>
      <div class="factory-stat">
        <span>运行任务</span>
        <strong>{{ dashboard?.factory_status.running_tasks || 0 }}</strong>
      </div>
    </div>

    <div class="factory-actions">
      <el-progress
        class="factory-progress"
        :percentage="progressPercent"
        :show-text="false"
        :stroke-width="8"
      />
      <p v-if="error" class="factory-error">{{ error }}</p>
      <div class="factory-buttons">
        <el-button :icon="Refresh" :loading="loading" plain @click="emit('refresh')">刷新</el-button>
        <el-button
          type="primary"
          :icon="action?.intent === 'repair' ? Tools : undefined"
          :disabled="!action"
          @click="action && emit('action', action.intent)"
        >
          {{ action?.label || '加载中' }}
        </el-button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.factory-control-panel {
  display: grid;
  grid-template-columns: minmax(240px, 1.2fr) minmax(320px, 1.4fr) minmax(260px, 1fr);
  gap: 14px;
  align-items: center;
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-surface);
}

.factory-identity {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.factory-icon {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  border-radius: 8px;
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.factory-title-block {
  min-width: 0;
}

.factory-kicker,
.factory-stat span {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 12px;
}

h2 {
  margin: 4px 0 0;
  font-size: 20px;
  line-height: 1.25;
}

.factory-mode-select {
  width: 150px;
  margin-top: 8px;
}

.factory-status-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.factory-stat {
  min-width: 0;
  padding: 8px 10px;
  border-radius: 8px;
  background: var(--color-bg-surface-muted);
}

.factory-stat strong {
  display: block;
  margin-top: 4px;
  font-size: 16px;
}

.factory-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.factory-progress {
  width: 100%;
}

.factory-error {
  margin: 0;
  color: var(--color-danger);
  font-size: 12px;
}

.factory-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

@media (max-width: 1180px) {
  .factory-control-panel {
    grid-template-columns: 1fr;
  }
}
</style>
