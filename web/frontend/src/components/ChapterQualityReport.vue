<script setup lang="ts">
import { computed } from 'vue'
import { CircleCheck, InfoFilled, Warning } from '@element-plus/icons-vue'

const props = defineProps<{
  qualityReport: Record<string, any>
}>()

const hasReport = computed(() => {
  return props.qualityReport && Object.keys(props.qualityReport).length > 0
})

const overallScore = computed(() => {
  return props.qualityReport?.overall_score || 0
})

const overallPass = computed(() => {
  return props.qualityReport?.overall_pass || false
})

const checks = computed(() => {
  return props.qualityReport?.checks || {}
})

const guardSummary = computed(() => {
  return props.qualityReport?.guard_summary || null
})

const guardResults = computed(() => {
  return guardSummary.value?.results || []
})

const blockedBy = computed(() => {
  return guardSummary.value?.blocked_by || []
})

const getGuardType = (status: string | number) => {
  const value = String(status)
  if (value === 'PASS') return 'success'
  if (value === 'WARN') return 'warning'
  if (value === 'FAIL') return 'danger'
  return 'info'
}

const getGuardLabel = (status: string | number) => {
  const value = String(status)
  if (value === 'PASS') return '通过'
  if (value === 'WARN') return '警告'
  if (value === 'FAIL') return '未通过'
  return value
}

const getCheckLabel = (key: string | number) => {
  const labels: Record<string, string> = {
    continuity_physical: '物理连续性',
    style: '文风检查',
    layout: '段落布局',
    scene_delta: '场景推进',
  }
  return labels[String(key)] || String(key)
}

const getLevelType = (level: string | number) => {
  const levelStr = String(level)
  if (levelStr === 'none') return 'success'
  if (levelStr === 'warning') return 'warning'
  if (levelStr === 'review') return 'info'
  if (levelStr === 'fail') return 'danger'
  return 'info'
}

const getLevelLabel = (level: string | number) => {
  const levelStr = String(level)
  if (levelStr === 'none') return '通过'
  if (levelStr === 'warning') return '警告'
  if (levelStr === 'review') return '需审阅'
  if (levelStr === 'fail') return '未通过'
  return levelStr
}
</script>

<template>
  <div class="quality-report-container">
    <div v-if="!hasReport" class="empty-state-card">
      <el-icon><InfoFilled /></el-icon>
      <p>暂无质量报告数据。运行章节生成后将自动生成。</p>
    </div>

    <template v-else>
      <!-- Overall Score -->
      <div class="overall-score-card" :class="overallPass ? 'pass' : 'fail'">
        <div class="score-header">
          <el-icon v-if="overallPass"><CircleCheck /></el-icon>
          <el-icon v-else><Warning /></el-icon>
          <span class="score-label">综合质量评分</span>
        </div>
        <div class="score-value">{{ overallScore }}</div>
        <div class="score-mode">报告模式：{{ qualityReport.mode === 'report_only' ? '仅报告' : '强制' }}</div>
      </div>

      <div v-if="guardSummary" class="guard-summary-card" :class="'guard-' + guardSummary.overall_status">
        <div class="guard-summary-head">
          <div>
            <div class="guard-title">统一门禁结果</div>
            <div class="guard-subtitle">硬门禁失败时，本章不能视为符合要求。</div>
          </div>
          <el-tag :type="getGuardType(guardSummary.overall_status)" size="large">
            {{ getGuardLabel(guardSummary.overall_status) }}
          </el-tag>
        </div>

        <div v-if="blockedBy.length" class="blocked-list">
          <span>阻断项</span>
          <el-tag v-for="guard in blockedBy" :key="guard" type="danger" effect="plain">
            {{ guard }}
          </el-tag>
        </div>

        <div class="guard-results">
          <div v-for="guard in guardResults" :key="guard.guard" class="guard-result-row">
            <div class="guard-result-top">
              <div class="guard-result-main">
                <strong>{{ guard.title || guard.guard }}</strong>
                <span>L{{ guard.level }} · {{ guard.guard }}</span>
              </div>
              <el-tag :type="getGuardType(guard.status)" size="small">
                {{ getGuardLabel(guard.status) }}
              </el-tag>
            </div>
            <div v-if="guard.findings?.length" class="guard-findings">
              <div v-for="finding in guard.findings" :key="finding.code" class="guard-finding">
                <span>{{ finding.message }}</span>
                <em v-if="finding.suggestion">{{ finding.suggestion }}</em>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Check Details -->
      <div class="checks-grid">
        <div v-for="(check, key) in checks" :key="key" class="check-card">
          <div class="check-header">
            <span class="check-name">{{ getCheckLabel(key) }}</span>
            <el-tag :type="getLevelType(check.level)" size="small">
              {{ getLevelLabel(check.level) }}
            </el-tag>
          </div>
          <div class="check-score">
            <span class="score-num">{{ check.score }}</span>
            <span class="score-unit">分</span>
          </div>
          <div v-if="check.details?.length" class="check-details">
            <div v-for="(detail, idx) in check.details" :key="idx" class="detail-item">
              {{ detail }}
            </div>
          </div>
          <div v-if="check.missing_hooks?.length" class="check-hooks">
            <div class="hooks-title">缺失钩子：</div>
            <div v-for="(hook, idx) in check.missing_hooks" :key="idx" class="hook-item">
              [{{ hook.type }}] {{ hook.text }}
            </div>
          </div>
        </div>
      </div>

      <!-- 读者拟真评测反馈 -->
      <div v-if="qualityReport.reader_evaluations" class="reader-evaluations-section" style="margin-top: 24px;">
        <h3 style="font-size: 16px; font-weight: 700; color: #1a2129; margin-bottom: 16px;">🎭 读者群拟真质检报告</h3>
        <el-tabs type="border-card" class="reader-tabs" style="border-radius: 8px; overflow: hidden; box-shadow: 0 2px 12px 0 rgba(0,0,0,0.04)">
          <el-tab-pane 
            v-for="(evalData, key) in qualityReport.reader_evaluations" 
            :key="key" 
            :label="evalData.persona_name || key"
          >
            <!-- 评分与总评 -->
            <div class="reader-header" style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px dashed var(--color-border);">
              <div>
                <span style="font-size: 14px; color: var(--color-text-muted);">偏好分类：</span>
                <el-tag size="small" type="info">{{ evalData.persona_name }}</el-tag>
              </div>
              <div style="display: flex; align-items: baseline; gap: 4px;">
                <span style="font-size: 28px; font-weight: 800; color: #e6a23c;">{{ evalData.score }}</span>
                <span style="font-size: 13px; color: #909399;">/10分</span>
              </div>
            </div>

            <!-- 拟真读者弹幕反馈 -->
            <div class="danmaku-container" style="margin-bottom: 20px;">
              <h4 style="font-size: 13px; font-weight: 700; color: var(--color-text-muted); margin-bottom: 10px;">💬 拟真弹幕反馈</h4>
              <div style="display: flex; flex-direction: column; gap: 8px;">
                <div 
                  v-for="(msg, idx) in evalData.danmaku" 
                  :key="idx" 
                  class="danmaku-bubble"
                  style="background: var(--color-bg-hover); border-radius: 12px; padding: 8px 14px; font-size: 13px; color: var(--color-text); align-self: flex-start; max-width: 90%; position: relative;"
                >
                  {{ msg }}
                </div>
              </div>
            </div>

            <!-- 爽点与毒点 -->
            <el-row :gutter="16" style="margin-bottom: 16px;">
              <el-col :span="12">
                <div style="background: #f0f9eb; border: 1px solid rgba(82, 196, 26, 0.15); border-radius: 8px; padding: 12px;">
                  <h5 style="color: #52c41a; font-size: 13px; font-weight: 700; margin: 0 0 8px 0;">✨ 迎合爽点</h5>
                  <ul style="margin: 0; padding-left: 16px; font-size: 13px; color: #606266; line-height: 1.6;">
                    <li v-for="hl in evalData.highlights" :key="hl">{{ hl }}</li>
                    <li v-if="!evalData.highlights?.length">无明显爽点</li>
                  </ul>
                </div>
              </el-col>
              <el-col :span="12">
                <div style="background: #fef0f0; border: 1px solid rgba(245, 108, 108, 0.15); border-radius: 8px; padding: 12px;">
                  <h5 style="color: #f56c6c; font-size: 13px; font-weight: 700; margin: 0 0 8px 0;">⚡ 毒点/合理性瑕疵</h5>
                  <ul style="margin: 0; padding-left: 16px; font-size: 13px; color: #606266; line-height: 1.6;">
                    <li v-for="dl in evalData.dislikes" :key="dl">{{ dl }}</li>
                    <li v-if="!evalData.dislikes?.length">无明显毒点</li>
                  </ul>
                </div>
              </el-col>
            </el-row>

            <!-- 总评 -->
            <div style="background: #fafaf9; border: 1px solid var(--color-border); border-radius: 8px; padding: 12px; font-size: 13px; color: var(--color-text-muted); line-height: 1.5;">
              <strong>读者总结：</strong>{{ evalData.summary }}
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>

      <!-- Raw JSON -->
      <el-collapse class="raw-json-collapse">
        <el-collapse-item title="查看原始质量报告 JSON 数据" name="raw">
          <pre class="raw-json-pre">{{ JSON.stringify(qualityReport, null, 2) }}</pre>
        </el-collapse-item>
      </el-collapse>
    </template>
  </div>
</template>

<style scoped>
.quality-report-container {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.overall-score-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px;
  border-radius: 12px;
  text-align: center;
}

.overall-score-card.pass {
  background: linear-gradient(135deg, #f0f9eb 0%, #e8f5e9 100%);
  border: 1px solid rgba(82, 196, 26, 0.2);
}

.overall-score-card.fail {
  background: linear-gradient(135deg, #fef0f0 0%, #fbe9e7 100%);
  border: 1px solid rgba(245, 108, 108, 0.2);
}

.score-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #1a2129;
}

.score-header .el-icon {
  font-size: 20px;
}

.pass .score-header .el-icon { color: #52c41a; }
.fail .score-header .el-icon { color: #f56c6c; }

.score-value {
  font-size: 48px;
  font-weight: 800;
  margin: 12px 0;
}

.pass .score-value { color: #52c41a; }
.fail .score-value { color: #f56c6c; }

.score-mode {
  font-size: 13px;
  color: #909399;
}

.guard-summary-card {
  background: var(--color-bg-surface);
  border: 1px solid var(--border-light);
  border-radius: 10px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.guard-summary-card.guard-FAIL {
  border-color: rgba(245, 108, 108, 0.45);
  background: #fff7f6;
}

.guard-summary-card.guard-WARN {
  border-color: rgba(230, 162, 60, 0.45);
  background: #fffaf0;
}

.guard-summary-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.guard-title {
  font-size: 16px;
  font-weight: 700;
  color: #1a2129;
}

.guard-subtitle {
  margin-top: 4px;
  font-size: 13px;
  color: #606266;
}

.blocked-list {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 13px;
  color: #c45656;
}

.guard-results {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.guard-result-row {
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 8px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.72);
}

.guard-result-top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.guard-result-main {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.guard-result-main strong {
  font-size: 14px;
  color: #1a2129;
}

.guard-result-main span {
  font-size: 12px;
  color: #909399;
}

.guard-findings {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 10px;
}

.guard-finding {
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-size: 13px;
  color: #606266;
}

.guard-finding em {
  color: #c45656;
  font-style: normal;
}

.checks-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.check-card {
  background: var(--color-bg-surface);
  border: 1px solid var(--border-light);
  border-radius: 10px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.check-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.check-name {
  font-size: 15px;
  font-weight: 600;
  color: #1a2129;
}

.check-score {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.score-num {
  font-size: 32px;
  font-weight: 800;
  color: #1a2129;
}

.score-unit {
  font-size: 14px;
  color: #909399;
}

.check-details {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.detail-item {
  font-size: 13px;
  color: #606266;
  padding: 6px 10px;
  background: #fafafa;
  border-radius: 6px;
}

.check-hooks {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.hooks-title {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
}

.hook-item {
  font-size: 12px;
  color: #909399;
  padding: 4px 8px;
  background: #f5f5f5;
  border-radius: 4px;
}

.empty-state-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px;
  color: #909399;
  text-align: center;
}

.raw-json-collapse {
  margin-top: 16px;
  border: 1px solid var(--border-light);
  border-radius: 8px;
  overflow: hidden;
}

.raw-json-collapse :deep(.el-collapse-item__header) {
  padding: 0 16px;
  font-size: 12px;
  color: #909399;
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
</style>
