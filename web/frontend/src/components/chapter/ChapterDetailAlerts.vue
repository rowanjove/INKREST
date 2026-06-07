<script setup lang="ts">
import { EXTERNAL_AUDIT_HINT, INTERNAL_GATE_HINT } from '../../constants/repairWorkflow'

defineProps<{
  loadError: string
  chapter: any
  isQualityBlocked: boolean
  resumableFrom: string
  resumingAudit: boolean
  rerunningGate: boolean
  copying: boolean
}>()

const emit = defineEmits<{
  goWriter: []
  handleResumeAudit: []
  handleRerunGate: []
  openUnifiedGateTab: []
  handleCopyFullText: []
}>()
</script>

<template>
  <el-alert v-if="loadError" :title="loadError" type="warning" show-icon style="margin-bottom: 24px" />

  <el-alert
    v-if="chapter"
    type="info"
    :closable="false"
    show-icon
    class="dual-audit-banner"
    title="两道审核说明"
    style="margin-bottom: 12px"
  >
    <p>{{ INTERNAL_GATE_HINT }}</p>
    <p>{{ EXTERNAL_AUDIT_HINT }}</p>
  </el-alert>

  <el-alert
    v-if="chapter && isQualityBlocked"
    type="error"
    :closable="false"
    show-icon
    title="本章处于质量阻断状态"
    style="margin-bottom: 16px"
  >
    终稿与审校报告仍在磁盘上，但状态落库未提交。
    <template v-if="resumableFrom">可从「{{ resumableFrom }}」阶段恢复流水线。</template>
    <div class="blocked-actions">
      <el-button type="warning" size="small" @click="emit('goWriter')">写作页改稿</el-button>
      <el-button type="primary" size="small" :loading="resumingAudit" @click="emit('handleResumeAudit')">
        重试审校
      </el-button>
      <el-button size="small" plain :loading="rerunningGate" @click="emit('handleRerunGate')">
        只重跑门禁
      </el-button>
      <el-button size="small" @click="emit('openUnifiedGateTab')">查看统一门禁</el-button>
      <el-button size="small" plain :loading="copying" @click="emit('handleCopyFullText')">
        复制全文试审
      </el-button>
    </div>
  </el-alert>
</template>

<style scoped>
.blocked-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}
</style>