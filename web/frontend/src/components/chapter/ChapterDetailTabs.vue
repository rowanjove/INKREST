<script setup lang="ts">
import {
  Calendar,
  CircleCheck,
  Compass,
  InfoFilled,
  Location,
  SuccessFilled,
  Warning,
} from '@element-plus/icons-vue'
import ChapterContent from '../ChapterContent.vue'
import ChapterPlan from '../ChapterPlan.vue'
import ChapterAudit from '../ChapterAudit.vue'
import ChapterQualityReport from '../ChapterQualityReport.vue'
import ChapterUnifiedGate from '../ChapterUnifiedGate.vue'

defineProps<{
  chapter: any
  isQualityBlocked: boolean
  hasStateUpdates: boolean
  stateChangeCount: number
  parseMarkdown: (md: string) => string
}>()

const activeTab = defineModel<string>('activeTab', { required: true })
</script>

<template>
  <div class="detail-tabs-panel panel">
    <el-tabs v-model="activeTab" class="custom-detail-tabs">
      <el-tab-pane label="终稿正文" name="final">
        <ChapterContent
          :title="chapter.title"
          :chapter-id="chapter.chapter_id"
          :final-text="chapter.final_text"
        />
      </el-tab-pane>

      <el-tab-pane label="章节总结" name="summary">
        <div class="summary-container">
          <div class="md-preview" v-html="parseMarkdown(chapter.chapter_summary)" />
        </div>
      </el-tab-pane>

      <el-tab-pane label="章节计划" name="plan">
        <ChapterPlan :plan="chapter.plan" />
      </el-tab-pane>

      <el-tab-pane label="安全审校" name="audit">
        <ChapterAudit :audit="chapter.audit" />
      </el-tab-pane>

      <el-tab-pane name="unified_gate">
        <template #label>
          <span>统一门禁</span>
          <el-badge v-if="isQualityBlocked" is-dot class="tab-badge-dot" />
        </template>
        <ChapterUnifiedGate
          :unified-gate="chapter.unified_gate || {}"
          :artifact-status="chapter.artifact_status || []"
        />
      </el-tab-pane>

      <el-tab-pane label="连续性检查" name="continuity">
        <div class="continuity-tab-content">
          <div class="audit-status-bar" :class="chapter.continuity?.pass ? 'risk-低' : 'risk-高'">
            <el-icon v-if="chapter.continuity?.pass"><CircleCheck /></el-icon>
            <el-icon v-else><Warning /></el-icon>
            <span>
              检查状态:
              <strong>{{ chapter.continuity?.pass ? '通过 (逻辑自洽)' : '未通过 (发现冲突设定)' }}</strong>
            </span>
          </div>

          <div class="audit-issues-block">
            <h4 class="sub-section-title">逻辑一致性检查明细</h4>
            <div v-if="chapter.continuity?.issues?.length" class="issues-card-list">
              <div
                v-for="(issue, idx) in chapter.continuity.issues"
                :key="idx"
                class="issue-detail-card warning"
              >
                <span class="issue-badge">逻辑漏洞 #{{ Number(idx) + 1 }}</span>
                <p class="issue-desc-text">{{ issue }}</p>
              </div>
            </div>
            <div v-else class="success-audit-state">
              <el-icon><SuccessFilled /></el-icon>
              <p>情节人物设定完全连贯，未发现时空冲突、道具丢失或角色前后行为逻辑相悖的问题。</p>
            </div>
          </div>

          <el-collapse class="raw-json-collapse">
            <el-collapse-item title="查看原始连续性检查 JSON 数据" name="raw">
              <pre class="raw-json-pre">{{ JSON.stringify(chapter.continuity, null, 2) }}</pre>
            </el-collapse-item>
          </el-collapse>
        </div>
      </el-tab-pane>

      <el-tab-pane label="质量报告" name="quality">
        <ChapterQualityReport :quality-report="chapter.quality_report || {}" />
      </el-tab-pane>

      <el-tab-pane label="设定同步状态" name="state_update">
        <div class="state-update-content">
          <div class="state-update-summary">
            本章共同步设定库变动:
            <strong>{{ stateChangeCount }}</strong> 项变更。
          </div>

          <div v-if="hasStateUpdates" class="state-blocks-container">
            <div v-if="chapter.state_update.events?.length" class="state-block">
              <h4 class="state-title-icon"><el-icon><Calendar /></el-icon> 新增历史大事件</h4>
              <div class="state-items">
                <div v-for="evt in chapter.state_update.events" :key="evt.id" class="sub-state-item event">
                  <div class="sub-state-header">
                    <span class="s-id">{{ evt.id }}</span>
                    <span v-if="evt.characters?.length" class="s-characters">
                      涉及角色: {{ evt.characters.join(', ') }}
                    </span>
                  </div>
                  <p class="s-body">{{ evt.summary }}</p>
                </div>
              </div>
            </div>

            <div v-if="chapter.state_update.timeline_nodes?.length" class="state-block">
              <h4 class="state-title-icon"><el-icon><Location /></el-icon> 实体与地点卡片更新</h4>
              <div class="state-items">
                <div
                  v-for="node in chapter.state_update.timeline_nodes"
                  :key="node.id"
                  class="sub-state-item node"
                >
                  <div class="sub-state-header">
                    <span class="s-name">{{ node.name }}</span>
                    <span class="s-type">{{ node.type }}</span>
                  </div>
                  <p class="s-body">{{ node.description }}</p>
                </div>
              </div>
            </div>

            <div v-if="chapter.state_update.foreshadows?.length" class="state-block">
              <h4 class="state-title-icon"><el-icon><Compass /></el-icon> 伏笔状态流</h4>
              <div class="state-items">
                <div v-for="f in chapter.state_update.foreshadows" :key="f.id" class="sub-state-item foreshadow">
                  <div class="sub-state-header">
                    <span class="s-title">{{ f.title }}</span>
                    <span class="s-status" :class="f.status">
                      {{ f.status === 'open' ? '未回收' : '已回收' }}
                    </span>
                  </div>
                  <p class="s-body">{{ f.description }}</p>
                </div>
              </div>
            </div>
          </div>

          <div v-else class="empty-state-card">
            <el-icon><InfoFilled /></el-icon>
            <p>本章写入没有引起小说背景库或全局设定库的状态变化。</p>
          </div>

          <el-collapse class="raw-json-collapse">
            <el-collapse-item title="查看原始状态更新 JSON 数据" name="raw">
              <pre class="raw-json-pre">{{ JSON.stringify(chapter.state_update, null, 2) }}</pre>
            </el-collapse-item>
          </el-collapse>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.detail-tabs-panel {
  padding: 24px;
}

.custom-detail-tabs :deep(.el-tabs__header) {
  margin-bottom: 24px;
}

.summary-container {
  padding: 10px 20px;
}

.md-preview :deep(.md-h3) {
  font-size: 18px;
  font-weight: 700;
  color: #1a2129;
  margin: 24px 0 12px;
  border-left: 3px solid var(--primary);
  padding-left: 10px;
}

.md-preview :deep(.md-p) {
  font-size: 15px;
  line-height: 1.7;
  color: var(--text-main);
  margin-bottom: 14px;
}

.md-preview :deep(.md-ul) {
  margin-bottom: 16px;
  padding-left: 20px;
}

.md-preview :deep(.md-li) {
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-main);
  margin-bottom: 8px;
}

.continuity-tab-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.audit-status-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-radius: 10px;
  font-size: 14px;
}

.audit-status-bar.risk-低 {
  background: #f0f9eb;
  color: #52c41a;
  border: 1px solid rgba(82, 196, 26, 0.15);
}

.audit-status-bar.risk-高 {
  background: #fef0f0;
  color: #f56c6c;
  border: 1px solid rgba(245, 108, 108, 0.15);
}

.audit-issues-block {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.sub-section-title {
  font-size: 15px;
  font-weight: 700;
  color: #1a2129;
}

.issues-card-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.issue-detail-card {
  display: flex;
  gap: 12px;
  padding: 14px 18px;
  background: #fafafa;
  border-left: 4px solid var(--primary);
  border-radius: 0 8px 8px 0;
  border-top: 1px solid var(--border-light);
  border-right: 1px solid var(--border-light);
  border-bottom: 1px solid var(--border-light);
}

.issue-detail-card.warning {
  border-left-color: #e6a23c;
}

.issue-badge {
  font-size: 11px;
  font-weight: 700;
  color: var(--primary);
  background: var(--primary-light);
  padding: 2px 8px;
  border-radius: 4px;
  height: 20px;
}

.issue-detail-card.warning .issue-badge {
  color: #e6a23c;
  background: #fdf6ec;
}

.issue-desc-text {
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-main);
}

.success-audit-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px;
  border: 1px dashed var(--border-light);
  border-radius: 10px;
  color: var(--text-muted);
  background: #fafaf9;
}

.success-audit-state .el-icon {
  font-size: 36px;
  color: #52c41a;
}

.success-audit-state p {
  font-size: 13px;
}

.state-update-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.state-update-summary {
  background: #fafafa;
  border: 1px solid var(--border-light);
  padding: 12px 18px;
  border-radius: 8px;
  font-size: 14px;
}

.state-blocks-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.state-block {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.state-title-icon {
  font-size: 14px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #1a2129;
}

.state-items {
  display: grid;
  grid-template-columns: 1fr;
  gap: 12px;
}

.sub-state-item {
  border: 1px solid var(--border-light);
  border-radius: 8px;
  padding: 14px 18px;
  background: var(--color-bg-surface);
}

.sub-state-item.event {
  border-left: 3px solid #3498db;
}

.sub-state-item.node {
  border-left: 3px solid #2ecc71;
}

.sub-state-item.foreshadow {
  border-left: 3px solid #9b59b6;
}

.sub-state-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 12px;
}

.s-id,
.s-name {
  font-weight: 700;
  color: #1a2129;
}

.s-characters,
.s-type {
  color: var(--text-muted);
}

.s-body {
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-main);
}

.s-status {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
}

.s-status.open {
  background: #fdf6ec;
  color: #e6a23c;
}

.s-status.closed {
  background: #f0f9eb;
  color: #52c41a;
}

.raw-json-collapse {
  margin-top: 32px;
  border: 1px solid var(--border-light);
  border-radius: 8px;
  overflow: hidden;
}

.raw-json-collapse :deep(.el-collapse-item__header) {
  padding: 0 16px;
  font-size: 12px;
  color: var(--text-muted);
  background-color: #fafafa;
}

.raw-json-collapse :deep(.el-collapse-item__content) {
  padding: 16px;
  background-color: #f7f7f7;
}

.raw-json-pre {
  font-family: var(--font-mono);
  font-size: 12px;
  color: #333333;
  white-space: pre-wrap;
  line-height: 1.5;
}

.empty-state-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px;
  color: var(--text-muted);
  text-align: center;
}
</style>