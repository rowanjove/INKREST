<script setup lang="ts">
import { Timer, Warning, WarningFilled } from '@element-plus/icons-vue'

defineProps<{
  calibration: Record<string, any>
  allDebt: Array<Record<string, any> & { kind: string }>
}>()

const activeTab = defineModel<string>('activeTab', { required: true })
</script>

<template>
  <div class="workbench-pane">
    <div class="workbench-metrics" style="padding-top: 16px;">
      <div class="control-section-head control-section-compact">
        <h2 class="control-section-title">长篇指标（只读）</h2>
        <p class="control-section-hint">
          体量请改
          <el-button type="primary" link @click="activeTab = 'workbench'">工作台 · 体量架构</el-button>
          · 连载进阶见
          <el-button type="primary" link @click="activeTab = 'serialization'">连载运营</el-button>
        </p>
      </div>
      <div class="control-grid control-grid-compact">
        <section class="panel report-panel">
          <div class="panel-header panel-header-compact">
            <div class="panel-header-left">
              <el-icon class="panel-icon report-color"><Warning /></el-icon>
              <h2>校准报告</h2>
            </div>
          </div>
          <div class="panel-body-scroll">
            <div v-if="calibration.issues?.length" class="issue-list">
              <p v-for="issue in calibration.issues" :key="issue">
                <el-icon><WarningFilled /></el-icon>{{ issue }}
              </p>
            </div>
            <el-empty v-else description="指标正常" :image-size="56" />
          </div>
        </section>

        <section class="panel pace-panel">
          <div class="panel-header panel-header-compact">
            <div class="panel-header-left">
              <el-icon class="panel-icon pace-color"><Timer /></el-icon>
              <h2>节奏比例</h2>
            </div>
          </div>
          <div class="pace-grid pace-grid-compact">
            <div>
              <strong>{{ calibration.pacing?.counts?.setup || 0 }}</strong>
              <span>铺垫</span>
            </div>
            <div>
              <strong>{{ calibration.pacing?.counts?.build || 0 }}</strong>
              <span>蓄力</span>
            </div>
            <div>
              <strong>{{ calibration.pacing?.counts?.burst || 0 }}</strong>
              <span>爆发</span>
            </div>
            <div>
              <strong>{{ calibration.pacing?.counts?.transition || 0 }}</strong>
              <span>过渡</span>
            </div>
          </div>
          <p
            v-for="issue in calibration.pacing?.issues || []"
            :key="issue"
            class="muted-line muted-line-compact"
          >
            {{ issue }}
          </p>
        </section>

        <section class="panel debt-panel full-row">
          <div class="panel-header panel-header-compact">
            <div class="panel-header-left">
              <el-icon class="panel-icon debt-color"><WarningFilled /></el-icon>
              <h2>叙事债务</h2>
            </div>
          </div>
          <div class="panel-body-scroll debt-scroll">
            <div v-if="allDebt.length" class="debt-list debt-list-compact">
              <article
                v-for="item in allDebt.slice(0, 8)"
                :key="`${item.kind}-${item.id}`"
                :class="['debt-row', item.debt_status]"
              >
                <el-tag
                  :type="item.kind === '伏笔' ? 'danger' : item.kind === '秘密' ? 'warning' : 'info'"
                  size="small"
                >
                  {{ item.kind }}
                </el-tag>
                <strong>{{ item.title || item.id }}</strong>
                <span class="debt-desc">{{ item.description }}</span>
                <small>第 {{ item.chapter_id }} 章 · {{ item.debt_status || 'open' }}</small>
              </article>
            </div>
            <el-empty v-else description="暂无债务" :image-size="56" />
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.workbench-pane {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: min-content;
  padding-bottom: 8px;
}

.workbench-metrics {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow: hidden;
}

.control-section-head {
  margin-bottom: 10px;
}

.control-section-title {
  margin: 0;
  font-size: 17px;
  color: var(--color-text-strong);
}

.control-section-hint {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--color-text-muted);
}

.control-section-compact .control-section-title {
  font-size: 14px;
}

.control-section-compact .control-section-hint {
  margin-top: 2px;
  font-size: 12px;
}

.control-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.control-grid-compact {
  flex: 1;
  min-height: 0;
  gap: 10px;
  grid-template-rows: minmax(0, 1fr) minmax(0, 1.15fr);
}

.control-grid .panel {
  border: 1px solid var(--color-border);
  background: var(--color-bg-surface);
  border-radius: 10px;
  padding: 18px;
  min-height: 240px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
}

.control-grid-compact .panel {
  min-height: 0;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  width: 100%;
}

.panel-header-compact {
  margin-bottom: 8px !important;
}

.panel-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-header-left h2 {
  margin: 0 !important;
  font-size: 18px;
  color: var(--color-text-strong);
  font-weight: 750;
}

.panel-header-compact h2 {
  font-size: 14px !important;
}

.panel-body-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.panel-icon {
  font-size: 18px;
  padding: 6px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.report-color {
  color: var(--color-warning);
  background: #fef9c3;
}

.pace-color {
  color: var(--color-success);
  background: #ecfdf5;
}

.debt-color {
  color: var(--color-danger);
  background: #fef2f2;
}

.issue-list p {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 10px;
  color: #9a5033;
}

.pace-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}

.pace-grid div {
  background: var(--color-bg-surface-muted);
  border-radius: 8px;
  padding: 14px 10px;
  text-align: center;
  border: 1px solid var(--color-border-subtle);
}

.pace-grid strong {
  display: block;
  font-size: 24px;
  color: var(--color-text-strong);
}

.pace-grid span,
.muted-line {
  color: var(--color-text-muted);
  font-size: 13px;
}

.pace-grid-compact {
  gap: 8px;
}

.pace-grid-compact strong {
  font-size: 20px;
}

.muted-line-compact {
  font-size: 11px;
  margin: 4px 0 0;
}

.full-row {
  grid-column: 1 / -1;
}

.debt-list {
  display: grid;
  gap: 8px;
}

.debt-row {
  display: grid;
  grid-template-columns: 80px 200px 1fr 260px;
  gap: 12px;
  align-items: center;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 10px 12px;
}

.debt-row.overdue {
  border-color: #f0b7a2;
  background: #fff5f0;
}

.debt-row.due_soon {
  border-color: #f2d38c;
  background: #fffbef;
}

.debt-desc {
  font-size: 13px;
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
}

.debt-row span,
.debt-row small {
  color: var(--color-text-muted);
  font-size: 12px;
}

.debt-row strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.debt-list-compact .debt-row {
  padding: 8px 10px;
  gap: 4px;
}

.debt-list-compact .debt-desc {
  font-size: 12px;
  -webkit-line-clamp: 1;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

@media (max-width: 980px) {
  .control-grid {
    grid-template-columns: 1fr;
  }

  .debt-row {
    grid-template-columns: 1fr;
  }
}
</style>