<script setup lang="ts">
import { computed } from 'vue'
import { CircleCheck, InfoFilled, Warning } from '@element-plus/icons-vue'
import ChapterArtifactStatus from './ChapterArtifactStatus.vue'

const props = defineProps<{
  unifiedGate: Record<string, any>
  artifactStatus?: Array<Record<string, any>>
}>()

const hasGate = computed(() => props.unifiedGate && Object.keys(props.unifiedGate).length > 0)

const blocked = computed(() => Boolean(props.unifiedGate?.blocked))

const overallPass = computed(() => props.unifiedGate?.overall_pass !== false && !blocked.value)

const quality = computed(() => props.unifiedGate?.quality || {})

const audit = computed(() => props.unifiedGate?.audit || {})

const resumableFrom = computed(() => props.unifiedGate?.resumable_from || '')

const rewriteHints = computed(() => (props.unifiedGate?.rewrite_hints || '').trim())

const statusTagType = computed(() => (overallPass.value ? 'success' : blocked.value ? 'danger' : 'warning'))
</script>

<template>
  <div class="unified-gate-container">
    <ChapterArtifactStatus
      v-if="artifactStatus?.length"
      :artifacts="artifactStatus"
      class="artifact-block"
    />

    <div v-if="!hasGate" class="empty-state-card">
      <el-icon><InfoFilled /></el-icon>
      <p>暂无统一门禁报告。章节完成审校后将生成 <code>reports/unified_gate.json</code>。</p>
    </div>

    <template v-else>
      <el-alert
        v-if="blocked"
        type="error"
        :closable="false"
        show-icon
        title="质量门禁未通过，流水线已暂停落库"
      >
        <template v-if="resumableFrom">
          可从 <strong>{{ resumableFrom }}</strong> 阶段恢复（任务页或告警横幅中的「恢复审校」）。
        </template>
        <span v-else>请根据下方改写提示修订正文后重新运行审校。</span>
      </el-alert>

      <div class="gate-summary-card" :class="overallPass ? 'pass' : 'fail'">
        <div class="gate-summary-head">
          <el-icon v-if="overallPass"><CircleCheck /></el-icon>
          <el-icon v-else><Warning /></el-icon>
          <span class="gate-title">统一门禁</span>
          <el-tag :type="statusTagType" size="large">
            {{ blocked ? '已阻断' : overallPass ? '通过' : '待处理' }}
          </el-tag>
        </div>
        <div v-if="quality.blocked_by?.length" class="blocked-by">
          <span>阻断项：</span>
          <el-tag v-for="g in quality.blocked_by" :key="g" type="danger" effect="plain">{{ g }}</el-tag>
        </div>
      </div>

      <el-row :gutter="16">
        <el-col :span="12">
          <div class="sub-card">
            <h4>质量门禁</h4>
            <p>模式：{{ quality.mode || '—' }}</p>
            <p>综合：{{ quality.overall_pass ? '通过' : '未通过' }} · 得分 {{ quality.overall_score ?? '—' }}</p>
            <p>守卫状态：<el-tag size="small">{{ quality.guard_status || '—' }}</el-tag></p>
          </div>
        </el-col>
        <el-col :span="12">
          <div class="sub-card">
            <h4>审校摘要</h4>
            <p>风险：{{ audit.risk_level || '—' }}</p>
            <p>需定向重写：{{ audit.requires_rewrite ? '是' : '否' }}</p>
            <p>问题数：{{ audit.issue_count ?? 0 }}</p>
          </div>
        </el-col>
      </el-row>

      <div v-if="rewriteHints" class="hints-card">
        <h4>改写提示</h4>
        <pre class="hints-pre">{{ rewriteHints }}</pre>
      </div>

      <el-collapse class="raw-json-collapse">
        <el-collapse-item title="查看 unified_gate.json" name="raw">
          <pre class="raw-json-pre">{{ JSON.stringify(unifiedGate, null, 2) }}</pre>
        </el-collapse-item>
      </el-collapse>
    </template>
  </div>
</template>

<style scoped>
.unified-gate-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.artifact-block {
  margin-bottom: 4px;
}

.empty-state-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 40px;
  color: #909399;
  text-align: center;
}

.gate-summary-card {
  padding: 18px;
  border-radius: 10px;
  border: 1px solid var(--border-light);
}

.gate-summary-card.pass {
  background: #f0f9eb;
}

.gate-summary-card.fail {
  background: #fef0f0;
  border-color: rgba(245, 108, 108, 0.35);
}

.gate-summary-head {
  display: flex;
  align-items: center;
  gap: 10px;
}

.gate-title {
  font-size: 16px;
  font-weight: 700;
  flex: 1;
}

.blocked-by {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  font-size: 13px;
}

.sub-card {
  background: var(--color-bg-surface);
  border: 1px solid var(--border-light);
  border-radius: 8px;
  padding: 14px;
  font-size: 13px;
  color: #606266;
  line-height: 1.7;
}

.sub-card h4 {
  margin: 0 0 8px;
  font-size: 14px;
  color: #1a2129;
}

.hints-card {
  background: #fafaf9;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 14px;
}

.hints-card h4 {
  margin: 0 0 10px;
  font-size: 14px;
}

.hints-pre {
  margin: 0;
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.55;
  color: var(--color-text-muted);
  font-family: var(--font-mono, monospace);
}

.raw-json-collapse {
  border: 1px solid var(--border-light);
  border-radius: 8px;
  overflow: hidden;
}

.raw-json-pre {
  font-size: 12px;
  white-space: pre-wrap;
  margin: 0;
}
</style>