<script setup lang="ts">
import { computed } from 'vue'
import { ElIcon } from 'element-plus'
import {
  VideoPause,
  FirstAidKit,
  Document,
  Setting,
  House,
  ArrowRight,
  CircleCheck,
  Close,
} from '@element-plus/icons-vue'
import { usePetStore } from '../../stores/pet'
import { SHANSHAN_BATCH_PAUSE_HINT } from '../../constants/shanshanCopy'
import type { PetAction } from '../../composables/usePetBubbleView'
import { factoryCommandButtonTone } from '../../composables/useFactoryActions'
import { formatFactoryIntent } from '../../utils/factoryStatus'

defineProps<{
  diagnoseCollapsed: boolean
  onToggleDiagnoseCollapsed: () => void
  onStatusCardClick: () => void
  onOpenMonitorForBatch: () => void
  onNavigate: (route: string) => void
  onActionClick: (action: PetAction) => void
  onFactoryIntent: (intent: string) => void
  onFactoryRepair: (chapterId: string) => void
  onAbortRunningTask: () => void
}>()

const pet = usePetStore()

const factoryDashboard = computed(() => pet.context?.factory || null)
const factoryCommands = computed(() => factoryDashboard.value?.commands || [])
const factoryBrief = computed(() => factoryDashboard.value?.operator_brief || null)
const firstRepairItem = computed(() => factoryDashboard.value?.repair?.items?.[0] || null)

function briefTagClass(severity: string) {
  if (severity === 'danger') return 'danger'
  if (severity === 'warning') return 'warning'
  if (severity === 'success') return 'success'
  return 'info'
}
</script>

<template>
  <section class="tab-content-status">
    <div
      v-if="pet.novelBatchPaused && pet.context?.novel_batch"
      class="batch-pause-banner"
      role="button"
      tabindex="0"
      @click="onOpenMonitorForBatch"
      @keydown.enter="onOpenMonitorForBatch"
    >
      <div class="batch-pause-top">
        <el-icon class="batch-pause-icon"><VideoPause /></el-icon>
        <span class="batch-pause-tag">生成已暂停</span>
      </div>
      <p class="batch-pause-text">{{ SHANSHAN_BATCH_PAUSE_HINT(pet.context.novel_batch) }}</p>
      <span class="batch-pause-cta">去生产中心处理 →</span>
    </div>

    <div
      class="status-card-compact"
      :class="{
        clickable:
          pet.novelBatchPaused ||
          pet.latestFailedTask ||
          pet.context?.running_tasks?.length ||
          (pet.context?.pipeline_pending?.pending_total ?? 0) > 0,
      }"
      @click="onStatusCardClick"
    >
      <div class="status-title-row">
        <span
          class="status-indicator-dot"
          :class="{
            alert: pet.novelBatchPaused || pet.latestFailedTask || pet.lastError,
            busy: !pet.novelBatchPaused && pet.context?.running_tasks?.length,
          }"
        />
        <span class="status-text-bold">{{ pet.statusLabel }}</span>
        <span class="project-name-tag" @click.stop>{{ pet.context?.active_project?.name || '未选择项目' }}</span>

        <button
          v-if="pet.latestFailedTask"
          type="button"
          class="ignore-btn-mini"
          title="隐藏/忽略此错误"
          @click.stop="pet.ignoreFailedTask(pet.latestFailedTask.id)"
        >
          <el-icon :size="12"><Close /></el-icon>
        </button>
      </div>
      <div class="status-detail-desc">{{ pet.statusDetail }}</div>
      <div v-if="pet.context?.running_tasks?.length" class="running-task-actions">
        <button
          type="button"
          class="abort-task-btn"
          @click.stop="onAbortRunningTask()"
        >
          中止
        </button>
      </div>
    </div>

    <section v-if="factoryDashboard" class="factory-brief-box">
      <div class="factory-brief-head">
        <span class="factory-brief-kicker">工厂管家</span>
        <span
          v-if="factoryBrief"
          class="factory-brief-tag"
          :class="briefTagClass(factoryBrief.severity)"
        >
          {{ formatFactoryIntent(factoryBrief.next_intent) }}
        </span>
      </div>
      <p v-if="factoryBrief?.summary" class="factory-brief-summary">{{ factoryBrief.summary }}</p>
      <p v-if="firstRepairItem?.manual_hint" class="factory-repair-hint">
        {{ firstRepairItem.manual_hint }}
      </p>
      <div v-if="factoryCommands.length" class="factory-command-row">
        <button
          v-for="command in factoryCommands"
          :key="command.id"
          type="button"
          class="action-pill-mini"
          :class="factoryCommandButtonTone(command.tone) || 'default'"
          :title="command.reason"
          @click="onFactoryIntent(command.intent)"
        >
          {{ command.label }}
        </button>
      </div>
      <button
        v-if="firstRepairItem && firstRepairItem.recommended_action === 'auto_repair'"
        type="button"
        class="factory-repair-btn"
        @click="onFactoryRepair(firstRepairItem.chapter_id)"
      >
        自动修复 {{ firstRepairItem.title }}
      </button>
    </section>

    <div class="diagnose-box-compact">
      <div class="diagnose-header-row" @click="onToggleDiagnoseCollapsed">
        <div class="diagnose-title-group">
          <el-icon class="collapse-arrow" :class="{ open: !diagnoseCollapsed }"><ArrowRight /></el-icon>
          <el-icon class="diagnose-icon"><FirstAidKit /></el-icon>
          <span class="diagnose-title-text">系统诊断</span>
        </div>
        <button
          type="button"
          class="scan-btn-mini"
          :disabled="pet.diagnoseLoading"
          @click.stop="pet.runDiagnose()"
        >
          {{ pet.diagnoseLoading ? '诊断中...' : '重新诊断' }}
        </button>
      </div>

      <div v-show="!diagnoseCollapsed" class="diagnose-body-wrapper">
        <div
          v-if="!pet.diagnoseLoading && (!pet.diagnoseResult || pet.diagnoseResult.issues.length === 0)"
          class="diagnose-healthy-mini"
        >
          <el-icon color="#16a34a"><CircleCheck /></el-icon>
          <span>系统各项服务与创作环境良好</span>
        </div>

        <div v-else-if="!pet.diagnoseLoading && pet.diagnoseResult" class="diagnose-list-mini">
          <div
            v-for="(issue, index) in pet.diagnoseResult.issues"
            :key="index"
            class="diagnose-item-mini"
            :class="issue.level"
          >
            <span class="issue-bullet">•</span>
            <span class="issue-msg-mini">{{ issue.message }}</span>
          </div>

          <div v-if="pet.diagnoseResult.suggestions.length" class="suggestions-box-mini">
            <div class="suggestion-actions-mini">
              <button
                v-for="(sug, idx) in pet.diagnoseResult.suggestions"
                :key="idx"
                type="button"
                class="action-pill-mini"
                @click="onActionClick(sug)"
              >
                {{ sug.label }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <p class="status-scope-hint">待处理修章、续跑与任务日志以生产中心为准；山山负责说明与指路。</p>

    <section class="quick-actions-compact">
      <button
        type="button"
        class="nav-btn-compact"
        :class="{ primary: pet.novelBatchPaused }"
        @click="onNavigate('/production?tab=reviews')"
      >
        <span>🔧 修章</span>
      </button>
      <button type="button" class="nav-btn-compact" @click="onNavigate('/logs')">
        <el-icon><Document /></el-icon>
        <span>日志</span>
      </button>
      <button type="button" class="nav-btn-compact" @click="onNavigate('/config')">
        <el-icon><Setting /></el-icon>
        <span>配置</span>
      </button>
      <button type="button" class="nav-btn-compact" @click="onNavigate('/')">
        <el-icon><House /></el-icon>
        <span>主页</span>
      </button>
    </section>
  </section>
</template>

<style scoped>
.tab-content-status {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  justify-content: space-between;
  overflow: hidden;
}

.batch-pause-banner {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border-radius: var(--radius-md, 10px);
  border: 1px solid #fde68a;
  background: linear-gradient(180deg, #fffdf5 0%, #fffbf0 100%);
  cursor: pointer;
  flex: none;
  transition: all 0.18s ease;
}

.batch-pause-banner:hover {
  border-color: #f59e0b;
  box-shadow: 0 2px 8px rgba(245, 158, 11, 0.1);
}

.batch-pause-top {
  display: flex;
  align-items: center;
  gap: 6px;
}

.batch-pause-icon {
  font-size: 14px;
  color: #d97706;
}

.batch-pause-tag {
  font-size: 11px;
  font-weight: 700;
  color: #b45309;
}

.batch-pause-text {
  margin: 0;
  font-size: 11.5px;
  line-height: 1.45;
  color: #4b5563;
}

.batch-pause-cta {
  font-size: 11px;
  font-weight: 600;
  color: #d97706;
}

.status-scope-hint {
  margin: 0;
  font-size: 11px;
  line-height: 1.4;
  color: var(--color-text-subtle, #94a3b8);
  text-align: center;
  flex: none;
}

.status-card-compact {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 11px 13px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: var(--radius-md, 10px);
  background: var(--color-bg-surface, #ffffff);
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
  flex: none;
}

.status-card-compact.clickable {
  cursor: pointer;
  transition: all 0.18s ease;
}

.status-card-compact.clickable:hover {
  border-color: var(--color-primary, #c66f4f);
  background: var(--color-primary-soft, #fff9f6);
  box-shadow: 0 3px 10px rgba(198, 111, 79, 0.08);
}

.ignore-btn-mini {
  margin-left: 6px;
  border: none;
  background: transparent;
  color: var(--color-text-subtle, #94a3b8);
  cursor: pointer;
  padding: 3px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.18s ease;
}

.ignore-btn-mini:hover {
  background: rgba(0, 0, 0, 0.06);
  color: #ef4444;
}

.status-title-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.status-indicator-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #16a34a;
  box-shadow: 0 0 0 2px rgba(22, 163, 74, 0.2);
}

.status-indicator-dot.busy {
  background: var(--color-primary, #c66f4f);
  box-shadow: 0 0 0 2px var(--color-primary-muted, rgba(198, 111, 79, 0.2));
}

.status-indicator-dot.alert {
  background: #dc2626;
  box-shadow: 0 0 0 2px rgba(220, 38, 38, 0.2);
}

.status-text-bold {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text-strong, #0f172a);
}

.project-name-tag {
  margin-left: auto;
  font-size: 11px;
  font-weight: 600;
  background: var(--color-bg-hover, #f1f5f9);
  color: var(--color-text-muted, #64748b);
  padding: 2px 7px;
  border-radius: 5px;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-detail-desc {
  font-size: 12px;
  color: var(--color-text-muted, #64748b);
  line-height: 1.45;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.running-task-actions {
  margin-top: 6px;
  display: flex;
  justify-content: flex-end;
}

.abort-task-btn {
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
  padding: 3px 9px;
  font-size: 11px;
  font-weight: 600;
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.18s ease;
}

.abort-task-btn:hover {
  background: #fee2e2;
}

.factory-brief-box {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 12px;
  border: 1px solid var(--color-border-subtle, #edf0f4);
  border-radius: var(--radius-md, 10px);
  background: var(--color-bg-app, #f8fafc);
  flex: none;
}

.factory-brief-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.factory-brief-kicker {
  font-size: 12px;
  font-weight: 700;
  color: var(--color-text, #334155);
}

.factory-brief-tag {
  padding: 1.5px 7px;
  border-radius: 999px;
  font-size: 10.5px;
  font-weight: 700;
}

.factory-brief-tag.danger {
  color: #dc2626;
  background: #fef2f2;
}

.factory-brief-tag.warning {
  color: #d97706;
  background: #fffbeb;
}

.factory-brief-tag.success {
  color: #16a34a;
  background: #f0fdf4;
}

.factory-brief-tag.info {
  color: #0284c7;
  background: #f0f9ff;
}

.factory-brief-summary,
.factory-repair-hint {
  margin: 0;
  font-size: 11.5px;
  line-height: 1.45;
  color: var(--color-text-muted, #64748b);
}

.factory-command-row {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.factory-command-row .action-pill-mini.primary {
  border-color: var(--color-primary, #c66f4f);
  background: var(--color-primary, #c66f4f);
  color: #fff;
}

.factory-command-row .action-pill-mini.warning {
  border-color: #f59e0b;
  background: #fffbeb;
  color: #b45309;
}

.factory-command-row .action-pill-mini.danger {
  border-color: #ef4444;
  background: #fef2f2;
  color: #b91c1c;
}

.factory-command-row .action-pill-mini.success {
  border-color: #22c55e;
  background: #f0fdf4;
  color: #15803d;
}

.factory-repair-btn {
  align-self: flex-start;
  border: 1px solid var(--color-primary, #c66f4f);
  background: var(--color-primary-soft, #fff5f0);
  color: var(--color-primary, #c66f4f);
  padding: 3px 9px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.18s ease;
}

.factory-repair-btn:hover {
  background: var(--color-primary, #c66f4f);
  color: #fff;
}

.diagnose-box-compact {
  background: var(--color-bg-surface, #ffffff);
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: var(--radius-md, 10px);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.diagnose-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
  flex: none;
}

.diagnose-title-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.diagnose-icon {
  color: var(--color-primary, #c66f4f);
  font-size: 13px;
}

.diagnose-title-text {
  font-size: 12.5px;
  font-weight: 700;
  color: var(--color-text-strong, #0f172a);
}

.scan-btn-mini {
  border: 0;
  background: transparent;
  color: var(--color-primary, #c66f4f);
  font-size: 11.5px;
  font-weight: 600;
  cursor: pointer;
  padding: 2px 4px;
  border-radius: 4px;
  transition: all 0.18s ease;
}

.scan-btn-mini:hover:not(:disabled) {
  background: var(--color-primary-soft, #fff5f0);
}

.diagnose-healthy-mini {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #15803d;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 12px;
  flex: 1;
}

.diagnose-list-mini {
  display: flex;
  flex-direction: column;
  gap: 5px;
  flex: 1;
  overflow-y: auto;
}

.diagnose-item-mini {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 6px 9px;
  border-radius: 6px;
  font-size: 11.5px;
  line-height: 1.45;
}

.diagnose-item-mini.error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
}

.diagnose-item-mini.warning {
  background: #fffbeb;
  border: 1px solid #fde68a;
  color: #b45309;
}

.issue-bullet {
  font-size: 13px;
  line-height: 1;
}

.issue-msg-mini {
  flex: 1;
}

.suggestions-box-mini {
  margin-top: 4px;
}

.suggestion-actions-mini {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.action-pill-mini {
  border: 1px solid var(--color-border, #d1d9e5);
  background: var(--color-bg-surface, #ffffff);
  color: var(--color-text, #334155);
  padding: 2.5px 8px;
  border-radius: 99px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.18s ease;
}

.action-pill-mini:hover {
  background: var(--color-primary, #c66f4f);
  color: #ffffff;
  border-color: var(--color-primary, #c66f4f);
}

.quick-actions-compact {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
  flex: none;
}

.nav-btn-compact {
  height: 32px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: var(--radius-sm, 7px);
  background: var(--color-bg-surface, #ffffff);
  color: var(--color-text, #334155);
  font-size: 11.5px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  cursor: pointer;
  transition: all 0.18s ease;
}

.nav-btn-compact:hover {
  border-color: var(--color-primary, #c66f4f);
  color: var(--color-primary, #c66f4f);
  background: var(--color-primary-soft, #fff5f0);
}

.nav-btn-compact.primary {
  border-color: #f59e0b;
  background: #fffbeb;
  color: #b45309;
}

.nav-btn-compact.primary:hover {
  background: #fef3c7;
}

.collapse-arrow {
  display: inline-flex;
  font-size: 11px;
  color: var(--color-text-subtle, #94a3b8);
  transition: transform 0.2s ease;
  transform: rotate(0deg);
}

.collapse-arrow.open {
  transform: rotate(90deg);
}
</style>
