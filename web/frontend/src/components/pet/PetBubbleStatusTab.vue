<script setup lang="ts">
import { computed } from 'vue'
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
      <span class="batch-pause-icon">⏸</span>
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
          ×
        </button>
      </div>
      <div class="status-detail-desc">{{ pet.statusDetail }}</div>
      <div v-if="pet.context?.running_tasks?.length" style="margin-top: 8px; display: flex; justify-content: flex-end;">
        <button
          type="button"
          class="action-pill-mini"
          style="background: #fef0f0; color: #f56c6c; border: 1px solid #fde2e2; padding: 4px 10px; font-size: 11px; border-radius: 4px; cursor: pointer; transition: all 0.2s;"
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
      <div class="diagnose-header-row" style="cursor: pointer; user-select: none;" @click="onToggleDiagnoseCollapsed">
        <div style="display: flex; align-items: center; gap: 6px;">
          <span class="collapse-arrow" :class="{ open: !diagnoseCollapsed }">▶</span>
          <span class="diagnose-title-text">🩺 系统诊断</span>
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
          <span class="icon-healthy-mini">✓</span>
          <span>系统健康状态良好。</span>
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
        <span>📑 日志</span>
      </button>
      <button type="button" class="nav-btn-compact" @click="onNavigate('/config')">
        <span>⚙️ 配置</span>
      </button>
      <button type="button" class="nav-btn-compact" @click="onNavigate('/')">
        <span>🏠 主页</span>
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
  padding: 10px 11px;
  border-radius: 8px;
  border: 1px solid #f5dab1;
  background: linear-gradient(180deg, #fdf6ec 0%, #fff 100%);
  cursor: pointer;
  flex: none;
}

.batch-pause-banner:hover {
  border-color: #e6a23c;
}

.batch-pause-icon {
  font-size: 12px;
  color: #e6a23c;
}

.batch-pause-text {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  color: #606266;
}

.batch-pause-cta {
  font-size: 11px;
  font-weight: 600;
  color: #b88230;
}

.status-scope-hint {
  margin: 0;
  font-size: 11px;
  line-height: 1.4;
  color: #909399;
  flex: none;
}

.status-card-compact {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 11px;
  border: 1px solid #e4eaf2;
  border-radius: 8px;
  background: var(--color-bg-surface);
  flex: none;
}

.status-card-compact.clickable {
  cursor: pointer;
  transition: all 0.2s ease;
}

.status-card-compact.clickable:hover {
  border-color: rgba(0, 122, 255, 0.35);
  background: rgba(0, 122, 255, 0.02);
  box-shadow: 0 4px 12px rgba(0, 122, 255, 0.05);
}

.ignore-btn-mini {
  margin-left: 6px;
  border: none;
  background: transparent;
  color: #a0aec0;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.ignore-btn-mini:hover {
  background: rgba(0, 0, 0, 0.05);
  color: #e53e3e;
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
  background: #48a868;
  box-shadow: 0 0 0 2px rgba(72, 168, 104, 0.14);
}

.status-indicator-dot.busy {
  background: #4f7fc6;
  box-shadow: 0 0 0 2px rgba(79, 127, 198, 0.14);
}

.status-indicator-dot.alert {
  background: #d65d5d;
  box-shadow: 0 0 0 2px rgba(214, 93, 93, 0.14);
}

.status-text-bold {
  font-size: 13.5px;
  font-weight: 700;
  color: #1f2937;
}

.project-name-tag {
  margin-left: auto;
  font-size: 12px;
  font-weight: 600;
  background: var(--color-border-subtle);
  color: #4a5568;
  padding: 1.5px 7px;
  border-radius: 4px;
  max-width: 140px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-detail-desc {
  font-size: 12.5px;
  color: #536176;
  line-height: 1.45;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.factory-brief-box {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px;
  border: 1px solid #e4eaf2;
  border-radius: 8px;
  background: var(--color-bg-surface-muted);
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
  color: #4a5568;
}

.factory-brief-tag {
  padding: 2px 7px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
}

.factory-brief-tag.danger {
  color: #c53030;
  background: #fff5f5;
}

.factory-brief-tag.warning {
  color: #dd6b20;
  background: #fffaf0;
}

.factory-brief-tag.success {
  color: #2f855a;
  background: #f0fff4;
}

.factory-brief-tag.info {
  color: #2b6cb0;
  background: #ebf8ff;
}

.factory-brief-summary,
.factory-repair-hint {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  color: #536176;
}

.factory-command-row {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.factory-command-row .action-pill-mini.primary {
  border-color: #007aff;
  background: #007aff;
  color: #fff;
}

.factory-command-row .action-pill-mini.warning {
  border-color: #e6a23c;
  background: #fdf6ec;
  color: #b88230;
}

.factory-command-row .action-pill-mini.danger {
  border-color: #f56c6c;
  background: #fef0f0;
  color: #c53030;
}

.factory-command-row .action-pill-mini.success {
  border-color: #48a868;
  background: #f0fff4;
  color: #2f855a;
}

.factory-repair-btn {
  align-self: flex-start;
  border: 1px solid #007aff;
  background: #e6f0ff;
  color: #007aff;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
}

.factory-repair-btn:hover {
  background: #007aff;
  color: #fff;
}

.diagnose-box-compact {
  background: rgba(255, 255, 255, 0.65);
  border: 1px solid rgba(0, 0, 0, 0.05);
  border-radius: 8px;
  padding: 10px;
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
  flex: none;
}

.diagnose-title-text {
  font-size: 13px;
  font-weight: 750;
  color: #4a5568;
}

.scan-btn-mini {
  border: 0;
  background: transparent;
  color: #007aff;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  padding: 0;
}

.diagnose-healthy-mini {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #2f855a;
  background: #f0fff4;
  border: 1px solid #c6f6d5;
  padding: 6px 8px;
  border-radius: 6px;
  font-size: 12.5px;
  flex: 1;
}

.icon-healthy-mini {
  font-weight: bold;
  font-size: 13px;
}

.diagnose-list-mini {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
  overflow-y: auto;
}

.diagnose-item-mini {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  padding: 5px 8px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.4;
}

.diagnose-item-mini.error {
  background: #fff5f5;
  border: 1px solid #fed7d7;
  color: #c53030;
}

.diagnose-item-mini.warning {
  background: #fffaf0;
  border: 1px solid #feebc8;
  color: #dd6b20;
}

.issue-bullet {
  font-size: 14px;
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
  gap: 4px;
}

.action-pill-mini {
  border: 1px solid #007aff;
  background: #e6f0ff;
  color: #007aff;
  padding: 2.5px 9px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-pill-mini:hover {
  background: #007aff;
  color: var(--color-bg-surface);
}

.quick-actions-compact {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
  flex: none;
}

.nav-btn-compact {
  height: 30px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 6px;
  background: var(--color-bg-surface);
  color: #2d3748;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.nav-btn-compact:hover {
  border-color: rgba(0, 0, 0, 0.15);
  background: #f7fafc;
}

.nav-btn-compact.primary {
  border-color: #e6a23c;
  background: #fdf6ec;
  color: #b88230;
}

.nav-btn-compact.primary:hover {
  background: #faecd8;
}

.collapse-arrow {
  display: inline-block;
  font-size: 8px;
  color: #718096;
  transition: transform 0.2s ease;
  transform: rotate(0deg);
}

.collapse-arrow.open {
  transform: rotate(90deg);
}
</style>
