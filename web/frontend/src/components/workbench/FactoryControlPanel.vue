<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Refresh, Tools } from '@element-plus/icons-vue'
import type { FactoryDashboard, FactoryMode } from '../../types/factory'
import {
  factoryModeOptions,
  formatFactoryIntent,
  formatFactoryState,
  getFactoryPrimaryAction,
  getFactoryTone,
} from '../../utils/factoryStatus'

const props = defineProps<{
  dashboard: FactoryDashboard | null
  loading?: boolean
  savingMode?: boolean
  savingAuthorLabel?: boolean
  showAdvancedDetails?: boolean
  error?: string
}>()

const emit = defineEmits<{
  action: [intent: string]
  refresh: []
  modeChange: [mode: FactoryMode]
  authorLabelChange: [label: string]
  toggleAdvanced: []
}>()

const authorLabelDraft = ref('')
watch(
  () => props.dashboard?.project.author_label || '',
  (value) => {
    authorLabelDraft.value = value
  },
  { immediate: true },
)

const action = computed(() => props.dashboard ? getFactoryPrimaryAction(props.dashboard) : null)
const stateLabel = computed(() =>
  props.dashboard ? formatFactoryState(props.dashboard.factory_status.state) : '等待加载',
)
const tone = computed(() =>
  props.dashboard ? getFactoryTone(props.dashboard.factory_status.risk_level) : 'success',
)
const modeOptions = factoryModeOptions()
const automationLabel = computed(() => {
  const level = props.dashboard?.mode_profile.automation_level
  if (level === 'high') return '高自动化'
  if (level === 'managed') return '管理视角'
  return '平衡介入'
})
function briefTagType(severity: string) {
  if (severity === 'success') return 'success'
  if (severity === 'warning') return 'warning'
  if (severity === 'danger') return 'danger'
  return 'info'
}
function commandButtonType(tone: string) {
  if (tone === 'primary') return 'primary'
  if (tone === 'success') return 'success'
  if (tone === 'warning') return 'warning'
  if (tone === 'danger') return 'danger'
  return undefined
}
function exportCheckType(status: string) {
  if (status === 'ready') return 'success'
  if (status === 'warning') return 'warning'
  if (status === 'blocked') return 'danger'
  return 'info'
}
const progressPercent = computed(() => {
  const status = props.dashboard?.factory_status
  if (!status?.target_chapters) return 0
  return Math.min(100, Math.round((status.completed_chapters / status.target_chapters) * 100))
})
</script>

<template>
  <section class="factory-control-panel" data-tour="factory-control">
    <div class="factory-identity">
      <div class="factory-title-block">
        <p class="factory-kicker">生产模式</p>
        <h2>{{ dashboard?.project.name || 'AI 网文生产工厂' }}</h2>
        <div class="factory-controls">
          <el-input
            v-if="dashboard?.project.id"
            v-model="authorLabelDraft"
            class="factory-author-label"
            size="small"
            maxlength="24"
            show-word-limit
            clearable
            :disabled="savingAuthorLabel"
            placeholder="作者标签（多书区分）"
            @change="emit('authorLabelChange', authorLabelDraft.trim())"
          />
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
          <el-tag v-if="dashboard?.mode_profile" size="small" effect="plain">{{ automationLabel }}</el-tag>
        </div>
        <div v-if="showAdvancedDetails && dashboard?.mode_profile" class="factory-mode-profile">
          <span
            v-for="priority in dashboard.mode_profile.priorities"
            :key="priority"
            class="factory-mode-priority"
          >
            {{ priority }}
          </span>
        </div>
        <p v-if="showAdvancedDetails && dashboard?.mode_profile.operator_hint" class="factory-mode-hint">
          {{ dashboard.mode_profile.operator_hint }}
        </p>
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
        <el-button plain size="small" @click="emit('toggleAdvanced')">
          {{ showAdvancedDetails ? '收起高级指标' : '展开高级指标' }}
        </el-button>
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

    <div class="factory-brief-column">
        <div v-if="dashboard?.operator_brief" class="factory-operator-brief">
          <el-tag size="small" :type="briefTagType(dashboard.operator_brief.severity)" effect="dark">
            {{ formatFactoryIntent(dashboard.operator_brief.next_intent) }}
          </el-tag>
          <div>
            <strong>{{ dashboard.operator_brief.summary }}</strong>
            <span v-if="showAdvancedDetails">{{ dashboard.operator_brief.details }}</span>
          </div>
        </div>
        <div v-if="dashboard?.commands?.length" class="factory-command-row">
          <el-tooltip
            v-for="command in dashboard.commands"
            :key="command.id"
            :content="command.reason"
            placement="bottom"
          >
            <el-button
              class="factory-command-button"
              :type="commandButtonType(command.tone)"
              plain
              size="small"
              @click="emit('action', command.intent)"
            >
              {{ command.label }}
            </el-button>
          </el-tooltip>
        </div>
        <div v-if="showAdvancedDetails && dashboard?.export_check" class="factory-export-check">
          <el-tag size="small" :type="exportCheckType(dashboard.export_check.status)" effect="plain">
            导出总检
          </el-tag>
          <div class="factory-export-copy">
            <strong>{{ dashboard.export_check.primary_action }}</strong>
            <span v-if="dashboard.export_check.blockers.length">
              {{ dashboard.export_check.blockers.join('；') }}
            </span>
            <span v-else-if="dashboard.export_check.warnings.length">
              {{ dashboard.export_check.warnings.join('；') }}
            </span>
            <span v-else>TXT / EPUB 导出条件已就绪。</span>
          </div>
          <el-button
            size="small"
            plain
            :disabled="!dashboard.export_check.can_export"
            @click="emit('action', 'export')"
          >
            去导出
          </el-button>
        </div>
    </div>
  </section>
</template>

<style scoped>
.factory-control-panel {
  display: grid;
  grid-template-columns: minmax(250px, 0.9fr) minmax(440px, 1.2fr) minmax(360px, 0.95fr);
  gap: 12px;
  align-items: center;
  padding: 14px 16px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-surface);
}

.factory-identity {
  display: flex;
  align-items: center;
  min-width: 0;
}

.factory-author-label {
  width: 240px;
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
  font-size: 19px;
  line-height: 1.25;
}

.factory-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.factory-mode-select {
  width: 150px;
}

.factory-mode-profile {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.factory-mode-priority {
  max-width: 120px;
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.factory-mode-hint {
  max-width: 520px;
  margin: 8px 0 0;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.5;
}

.factory-brief-column {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.factory-operator-brief {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 8px;
  align-items: flex-start;
  margin: 0;
  padding: 8px;
  border-radius: 8px;
  background: var(--color-bg-surface-muted);
}

.factory-operator-brief strong,
.factory-operator-brief span {
  display: block;
}

.factory-operator-brief strong {
  font-size: 13px;
  line-height: 1.45;
}

.factory-operator-brief span {
  margin-top: 2px;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.5;
}

.factory-command-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin: 0;
}

.factory-command-button {
  max-width: 150px;
}

.factory-export-check {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  margin: 0;
  padding: 8px;
  border-radius: 8px;
  background: var(--color-bg-surface-muted);
}

.factory-export-copy {
  min-width: 0;
}

.factory-export-copy strong,
.factory-export-copy span {
  display: block;
}

.factory-export-copy strong {
  font-size: 13px;
  line-height: 1.4;
}

.factory-export-copy span {
  margin-top: 2px;
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.45;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.factory-status-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.factory-stat {
  min-width: 0;
  min-height: 60px;
  padding: 9px 10px;
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

@media (max-width: 1320px) {
  .factory-control-panel {
    grid-template-columns: minmax(260px, 0.9fr) minmax(420px, 1.1fr);
  }

  .factory-actions {
    grid-column: 1 / -1;
    display: grid;
    grid-template-columns: minmax(260px, 1fr) auto;
    align-items: center;
  }

  .factory-brief-column {
    grid-column: 1 / -1;
  }

  .factory-export-check {
    grid-template-columns: auto minmax(0, 1fr);
  }

  .factory-export-check .el-button {
    grid-column: 2;
    justify-self: start;
  }
}

@media (max-width: 900px) {
  .factory-control-panel {
    grid-template-columns: 1fr;
  }

  .factory-status-grid,
  .factory-actions {
    grid-column: auto;
    grid-template-columns: 1fr;
  }

  .factory-buttons {
    justify-content: flex-start;
  }
}
</style>
