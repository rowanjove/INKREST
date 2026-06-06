<script setup lang="ts">
import { ref } from 'vue'

withDefaults(
  defineProps<{
    /** 嵌入章节页卷级进度栏时使用紧凑排版 */
    embedded?: boolean
  }>(),
  { embedded: false },
)
import { ElMessage } from 'element-plus'
import { CopyDocument, Download } from '@element-plus/icons-vue'
import { exportChaptersTrial } from '../api'
import { copyPlainTextToClipboard } from '../utils/copyChapterText'
import { usePipelineAlertsStore } from '../stores/pipelineAlerts'

const exporting = ref(false)
const alertsStore = usePipelineAlertsStore()

const runExport = async (chapterIds?: string[]) => {
  exporting.value = true
  try {
    const { data } = await exportChaptersTrial({
      chapter_ids: chapterIds,
      include_titles: true,
    })
    await copyPlainTextToClipboard(data.text || '')
    ElMessage.success(
      `已复制 ${(data.chapter_ids || []).length} 章试发文本（约 ${data.char_count || 0} 字）`,
    )
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error.message || '导出失败')
  } finally {
    exporting.value = false
  }
}

const exportPending = async () => {
  const ids = alertsStore.alerts.map((a) => a.chapter_id).filter(Boolean)
  if (!ids.length) {
    ElMessage.info('当前无待处理章节，将导出全部有正文的章节')
  }
  await runExport(ids.length ? ids : undefined)
}

const exportAll = () => runExport()
</script>

<template>
  <section class="trial-export" :class="{ panel: !embedded, embedded }">
    <h3 class="export-title">
      <el-icon class="title-icon"><CopyDocument /></el-icon>
      平台试发 · 批量复制
    </h3>
    <p class="hint">
      合并多章正文到剪贴板，便于粘贴到网文平台试发/审核。外审通过后请在章节详情标记「外审已通过」。
    </p>
    <div class="actions">
      <el-button
        type="primary"
        class="action-btn primary-gradient"
        :icon="CopyDocument"
        :loading="exporting"
        @click="exportPending"
      >
        复制待处理章节
      </el-button>
      <el-button 
        class="action-btn secondary-btn" 
        :icon="Download" 
        plain 
        :loading="exporting" 
        @click="exportAll"
      >
        复制全书已有正文
      </el-button>
    </div>
  </section>
</template>

<style scoped>
.trial-export.panel {
  margin-bottom: 16px;
  padding: 18px 20px;
  border-radius: 12px;
  border: 1px solid var(--color-border, #e2e8f0);
  background: var(--color-bg-surface, #fff);
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05);
}

.trial-export.embedded {
  padding: 16px;
  background: var(--color-bg-surface-muted, #f8fafc);
  border: 1px solid var(--color-border-subtle, #e2e8f0);
  border-radius: 10px;
}

.export-title {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-strong, #1e293b);
}

.title-icon {
  color: var(--el-color-primary, #3b82f6);
}

.hint {
  margin: 0 0 14px;
  font-size: 12px;
  color: var(--color-text-muted, #64748b);
  line-height: 1.6;
}

.actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
}

.action-btn {
  width: 100%;
  margin-left: 0 !important; /* Override element-plus default button margin-left */
  height: 36px;
  font-size: 13px;
  font-weight: 500;
  border-radius: 6px;
  display: flex;
  justify-content: center;
  align-items: center;
  transition: all 0.2s ease;
}

.primary-gradient {
  background: linear-gradient(135deg, #ea580c 0%, #c2410c 100%) !important;
  border: none !important;
  color: #fff !important;
}

.primary-gradient:hover {
  opacity: 0.95;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(234, 88, 12, 0.2);
}

.secondary-btn {
  border-color: var(--color-border, #cbd5e1) !important;
  color: var(--color-text-normal, #334155) !important;
}

.secondary-btn:hover {
  color: #ea580c !important;
  border-color: #f97316 !important;
  background-color: #fff7ed !important;
}
</style>