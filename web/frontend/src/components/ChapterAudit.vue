<script setup lang="ts">
import { CircleCheck, SuccessFilled, Warning } from '@element-plus/icons-vue'

defineProps<{ audit: any }>()

const getIndexLabel = (index: any) => Number(index) + 1
</script>

<template>
  <div class="audit-tab-content">
    <div class="audit-status-bar" :class="'risk-' + audit?.risk_level">
      <el-icon v-if="audit?.risk_level === '低'"><CircleCheck /></el-icon>
      <el-icon v-else><Warning /></el-icon>
      <span>审核结果: 本章内容安全评级为 <strong>{{ audit?.risk_level || '未知' }}风险</strong></span>
    </div>

    <div class="audit-issues-block">
      <h4 class="sub-section-title">检测到的敏感信息 / 合规建议</h4>
      <div v-if="audit?.issues?.length" class="issues-card-list">
        <div v-for="(issue, idx) in audit.issues" :key="idx" class="issue-detail-card">
          <span class="issue-badge">建议 #{{ getIndexLabel(idx) }}</span>
          <p class="issue-desc-text">{{ issue }}</p>
        </div>
      </div>
      <div v-else class="success-audit-state">
        <el-icon><SuccessFilled /></el-icon>
        <p>未检测到任何敏感词汇、暴力、或者政策风险，内容完全合规。</p>
      </div>
    </div>

    <el-collapse class="raw-json-collapse">
      <el-collapse-item title="查看原始审校报告 JSON 数据" name="raw">
        <pre class="raw-json-pre">{{ JSON.stringify(audit, null, 2) }}</pre>
      </el-collapse-item>
    </el-collapse>
  </div>
</template>

<style scoped>
.audit-tab-content { display: flex; flex-direction: column; gap: 24px; }
.audit-status-bar {
  display: flex; align-items: center; gap: 12px;
  padding: 16px 20px; border-radius: 10px; font-size: 14px;
}
.audit-status-bar.risk-低 { background: #f0f9eb; color: #52c41a; border: 1px solid rgba(82, 196, 26, 0.15); }
.audit-status-bar.risk-中, .audit-status-bar.risk-高 { background: #fef0f0; color: #f56c6c; border: 1px solid rgba(245, 108, 108, 0.15); }
.audit-issues-block { display: flex; flex-direction: column; gap: 14px; }
.sub-section-title { font-size: 15px; font-weight: 700; color: #1a2129; }
.issues-card-list { display: flex; flex-direction: column; gap: 10px; }
.issue-detail-card {
  display: flex; gap: 12px; padding: 14px 18px; background: #fafafa;
  border-left: 4px solid var(--primary); border-radius: 0 8px 8px 0;
  border-top: 1px solid var(--border-light); border-right: 1px solid var(--border-light);
  border-bottom: 1px solid var(--border-light);
}
.issue-badge {
  font-size: 11px; font-weight: 700; color: var(--primary);
  background: var(--primary-light); padding: 2px 8px; border-radius: 4px; height: 20px;
}
.issue-desc-text { font-size: 13px; line-height: 1.5; color: var(--text-main); }
.success-audit-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 12px; padding: 40px; border: 1px dashed var(--border-light);
  border-radius: 10px; color: var(--text-muted); background: #fafaf9;
}
.success-audit-state .el-icon { font-size: 36px; color: #52c41a; }
.success-audit-state p { font-size: 13px; }

.raw-json-collapse { margin-top: 32px; border: 1px solid var(--border-light); border-radius: 8px; overflow: hidden; }
.raw-json-collapse :deep(.el-collapse-item__header) { padding: 0 16px; font-size: 12px; color: var(--text-muted); background-color: #fafafa; }
.raw-json-collapse :deep(.el-collapse-item__content) { padding: 16px; background-color: #f7f7f7; }
.raw-json-pre { font-family: var(--font-mono); font-size: 12px; color: #333333; white-space: pre-wrap; line-height: 1.5; }
</style>
