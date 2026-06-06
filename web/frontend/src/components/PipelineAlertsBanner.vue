<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { CopyDocument, Edit, Refresh, Warning } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  dismissPipelineAlert,
  getChapter,
  rerunChapterGate,
  resumeChapterAudit,
  setChapterExternalReview,
  rewriteBatchChapters,
} from '../api'
import { usePipelineAlerts, formatAlertStage } from '../composables/usePipelineAlerts'
import { usePipelineAlertsStore } from '../stores/pipelineAlerts'
import { copyChapterPlainText } from '../utils/copyChapterText'
import { DUAL_AUDIT_HINT } from '../constants/repairWorkflow'

const props = withDefaults(
  defineProps<{
    pollIntervalMs?: number
    showActions?: boolean
    /** navigate: 跳转写作台；emit: 由父组件处理（写作台内切换章节） */
    selectMode?: 'navigate' | 'emit'
  }>(),
  {
    pollIntervalMs: 4000,
    showActions: true,
    selectMode: 'navigate',
  },
)

const emit = defineEmits<{
  selectChapter: [chapterId: string]
}>()

const router = useRouter()
const alertsStore = usePipelineAlertsStore()
const { pipelineAlerts } = usePipelineAlerts(props.pollIntervalMs)
const resumingId = ref<string | null>(null)
const gateRerunId = ref<string | null>(null)
const dismissingId = ref<string | null>(null)
const copyingId = ref<string | null>(null)

// --- Selection & Bulk Actions ---
const selectedIds = ref<string[]>([])
const isProcessingBulk = ref(false)
const bulkProgress = ref({ current: 0, total: 0 })

const handleBulkProcess = async () => {
  const targets = selectedIds.value.length > 0
    ? [...selectedIds.value]
    : pipelineAlerts.value.map((a) => a.chapter_id).filter(Boolean)

  if (targets.length === 0) {
    ElMessage.warning('没有可处理的章节')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要批量将 ${targets.length} 个章节按最新的修改设计方案依次重跑吗？\n(注意：该操作会清空当前这几章的生成断点，从头重写)`,
      '批量处理确认',
      {
        confirmButtonText: '确定重跑',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
  } catch {
    return
  }

  isProcessingBulk.value = true
  bulkProgress.value = { current: 0, total: targets.length }

  try {
    const { data } = await rewriteBatchChapters(targets)
    ElMessage.success(`已成功提交批量重跑任务，批次 ID: ${data.batch_id}，请到日志中心查看任务流水`)
    selectedIds.value = selectedIds.value.filter((id) => !targets.includes(id))
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error.message || '批量重跑提交失败')
  } finally {
    isProcessingBulk.value = false
    await alertsStore.fetchAlerts()
  }
}


const isQualityBlocked = (item: { last_stage?: string; quality?: { blocked_by?: string[] } }) =>
  item.last_stage === 'quality_blocked' ||
  Boolean(item.quality?.blocked_by?.length)

const isBatchRetry = (item: { last_stage?: string }) => item.last_stage === 'batch_retry'

const isExternalPending = (item: { last_stage?: string }) =>
  item.last_stage === 'external_review_pending'

const needsRepairActions = (item: { last_stage?: string; quality?: { blocked_by?: string[] } }) =>
  isQualityBlocked(item) || isBatchRetry(item) || isExternalPending(item)

const selectedItems = computed(() =>
  pipelineAlerts.value.filter((item) => selectedIds.value.includes(item.chapter_id))
)

const isAllSelected = computed(() => {
  return pipelineAlerts.value.length > 0 && selectedIds.value.length === pipelineAlerts.value.length
})

const isIndeterminate = computed(() => {
  return selectedIds.value.length > 0 && selectedIds.value.length < pipelineAlerts.value.length
})

const toggleSelectAll = (val: boolean) => {
  if (val) {
    selectedIds.value = pipelineAlerts.value.map((item) => item.chapter_id)
  } else {
    selectedIds.value = []
  }
}

const handleCheckboxChange = (chapterId: string, checked: boolean) => {
  if (checked) {
    if (!selectedIds.value.includes(chapterId)) {
      selectedIds.value = [...selectedIds.value, chapterId]
    }
  } else {
    selectedIds.value = selectedIds.value.filter((id) => id !== chapterId)
  }
}

// Cleanup selectedIds when alerts list changes
watch(pipelineAlerts, (newAlerts) => {
  const currentIds = newAlerts.map((item) => item.chapter_id)
  selectedIds.value = selectedIds.value.filter((id) => currentIds.includes(id))
}, { deep: true })

// Bulk action targets calculations
const bulkResumeTargets = computed(() => selectedIds.value)

const bulkRerunGateTargets = computed(() =>
  selectedItems.value
    .filter((item) => !isExternalPending(item))
    .map((item) => item.chapter_id)
)

const bulkExternalPassedTargets = computed(() =>
  selectedItems.value
    .filter((item) => isExternalPending(item))
    .map((item) => item.chapter_id)
)

const bulkDismissTargets = computed(() => selectedIds.value)

const runBatchTask = async (
  actionName: string,
  targets: string[],
  actionFn: (id: string) => Promise<any>
) => {
  if (targets.length === 0) return
  isProcessingBulk.value = true
  bulkProgress.value = { current: 0, total: targets.length }
  let successCount = 0
  let failCount = 0
  const errors: string[] = []

  const promises = targets.map(async (id) => {
    try {
      await actionFn(id)
      successCount++
    } catch (error: any) {
      failCount++
      const msg = error?.response?.data?.detail || error.message || '操作失败'
      errors.push(`第 ${id} 章: ${msg}`)
    } finally {
      bulkProgress.value.current++
    }
  })

  await Promise.all(promises)

  if (successCount > 0) {
    ElMessage.success(`成功对 ${successCount} 个章节执行 [${actionName}]`)
  }
  if (failCount > 0) {
    ElMessage.error(`${failCount} 个章节执行失败:\n${errors.join('\n')}`)
  }

  selectedIds.value = selectedIds.value.filter(id => !targets.includes(id))
  isProcessingBulk.value = false
  await alertsStore.fetchAlerts()
}

const bulkResumeAudit = () => {
  runBatchTask('重试审校', bulkResumeTargets.value, resumeChapterAudit)
}

const bulkRerunGate = () => {
  runBatchTask('重跑门禁', bulkRerunGateTargets.value, rerunChapterGate)
}

const bulkExternalPassed = () => {
  runBatchTask('外审已通过', bulkExternalPassedTargets.value, (id) =>
    setChapterExternalReview(id, { status: 'external_passed' })
  )
}

const bulkDismissAlert = () => {
  runBatchTask('标记已处理', bulkDismissTargets.value, dismissPipelineAlert)
}

// --- Individual Chapter Actions ---
const copyBodyForPlatform = async (chapterId: string) => {
  copyingId.value = chapterId
  try {
    const { data } = await getChapter(chapterId)
    const len = await copyChapterPlainText({
      chapter_id: data.chapter_id,
      title: data.title,
      final_text: data.final_text,
    })
    ElMessage.success(`已复制第 ${chapterId} 章全文（约 ${len} 字），可粘贴到网文平台试审`)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error.message || '复制失败')
  } finally {
    copyingId.value = null
  }
}

const openChapter = (chapterId: string, tab?: string) => {
  if (props.selectMode === 'emit') {
    emit('selectChapter', chapterId)
    return
  }
  const query: Record<string, string> = { chapter: chapterId }
  if (tab) query.tab = tab
  router.push({ path: '/writer', query })
}

const openUnifiedGate = (chapterId: string) => {
  router.push({ path: `/chapters/${chapterId}`, query: { tab: 'unified_gate' } })
}

const dismissAlert = async (chapterId: string) => {
  dismissingId.value = chapterId
  try {
    await dismissPipelineAlert(chapterId)
    ElMessage.success(`第 ${chapterId} 章告警已标记为已处理`)
    await alertsStore.fetchAlerts()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error.message || '操作失败')
  } finally {
    dismissingId.value = null
  }
}

const rerunGate = async (chapterId: string) => {
  gateRerunId.value = chapterId
  try {
    await rerunChapterGate(chapterId)
    ElMessage.success(`第 ${chapterId} 章已提交「只重跑门禁」，请到章节维护或日志中心查看`)
    await alertsStore.fetchAlerts()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error.message || '提交失败')
  } finally {
    gateRerunId.value = null
  }
}

const markExternalPassed = async (chapterId: string) => {
  try {
    await setChapterExternalReview(chapterId, { status: 'external_passed' })
    ElMessage.success(`第 ${chapterId} 章已标记外审通过`)
    await alertsStore.fetchAlerts()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error.message || '标记失败')
  }
}

const resumeAudit = async (chapterId: string) => {
  resumingId.value = chapterId
  try {
    await resumeChapterAudit(chapterId)
    ElMessage.success(`第 ${chapterId} 章已提交重试审校，请到章节维护或日志中心查看`)
    await alertsStore.fetchAlerts()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error.message || '提交失败')
  } finally {
    resumingId.value = null
  }
}
</script>

<template>
  <section
    v-if="pipelineAlerts.length > 0"
    id="pipeline-alerts-section"
    class="pipeline-alerts-banner"
  >
    <div class="banner-head">
      <el-checkbox
        :model-value="isAllSelected"
        :indeterminate="isIndeterminate"
        @change="toggleSelectAll"
        class="bulk-checkbox"
      />
      <el-icon class="banner-icon"><Warning /></el-icon>
      <div class="banner-title-area">
        <strong>待处理章节</strong>
        <span class="banner-sub">门禁阻断 / 批量跳过 · 改稿后重试审校，通过后再「继续写书」</span>
      </div>
      <el-tag type="danger" size="small">{{ pipelineAlerts.length }} 项</el-tag>
      <el-button
        type="primary"
        size="small"
        :icon="Refresh"
        style="margin-left: 10px;"
        :loading="isProcessingBulk"
        @click="handleBulkProcess"
      >
        批量处理
      </el-button>
    </div>
    <p class="banner-audit-hint">{{ DUAL_AUDIT_HINT }}</p>

    <!-- Bulk Actions Panel -->
    <transition name="fade">
      <div v-if="selectedIds.length > 0" class="bulk-actions-bar">
        <span class="selected-count">已选择 {{ selectedIds.length }} 章</span>
        <div class="bulk-buttons">
          <el-button
            v-if="bulkResumeTargets.length > 0"
            type="warning"
            size="small"
            :loading="isProcessingBulk"
            @click="bulkResumeAudit"
          >
            批量重试审校 ({{ bulkResumeTargets.length }})
          </el-button>
          <el-button
            v-if="bulkRerunGateTargets.length > 0"
            type="success"
            size="small"
            :loading="isProcessingBulk"
            @click="bulkRerunGate"
          >
            批量重跑门禁 ({{ bulkRerunGateTargets.length }})
          </el-button>
          <el-button
            v-if="bulkExternalPassedTargets.length > 0"
            type="success"
            size="small"
            :loading="isProcessingBulk"
            @click="bulkExternalPassed"
          >
            批量外审已通过 ({{ bulkExternalPassedTargets.length }})
          </el-button>
          <el-button
            v-if="bulkDismissTargets.length > 0"
            type="info"
            size="small"
            :loading="isProcessingBulk"
            @click="bulkDismissAlert"
          >
            批量忽略 ({{ bulkDismissTargets.length }})
          </el-button>
        </div>
        <div v-if="isProcessingBulk" class="bulk-progress-text">
          处理中... ({{ bulkProgress.current }}/{{ bulkProgress.total }})
        </div>
      </div>
    </transition>

    <ul class="alert-list">
      <li v-for="item in pipelineAlerts" :key="item.chapter_id" class="alert-item">
        <div class="alert-main">
          <el-checkbox
            :model-value="selectedIds.includes(item.chapter_id)"
            @change="(val: boolean) => handleCheckboxChange(item.chapter_id, val)"
            class="item-checkbox"
          />
          <el-tag type="danger" size="small" effect="plain">
            {{ formatAlertStage(item.last_stage) }}
          </el-tag>
          <span
            class="chapter-label"
            :class="{ clickable: selectMode === 'emit' }"
            @click="selectMode === 'emit' ? openChapter(item.chapter_id) : undefined"
          >第 {{ item.chapter_id }} 章</span>
          <span class="alert-msg">{{ item.message }}</span>
          <span
            v-if="item.quality?.blocked_by?.length"
            class="alert-detail"
          >
            阻断项: {{ item.quality.blocked_by.join(', ') }}
          </span>
        </div>
        <div v-if="showActions" class="alert-actions">
          <template v-if="needsRepairActions(item)">
            <el-button type="info" link :icon="Edit" @click="openChapter(item.chapter_id)">
              {{ selectMode === 'emit' ? '改正文' : '写作页改稿' }}
            </el-button>
            <el-button
              type="warning"
              link
              :icon="Refresh"
              :loading="resumingId === item.chapter_id"
              @click="resumeAudit(item.chapter_id)"
            >
              重试审校
            </el-button>
            <el-button
              v-if="!isExternalPending(item)"
              type="success"
              link
              :loading="gateRerunId === item.chapter_id"
              @click="rerunGate(item.chapter_id)"
            >
              只重跑门禁
            </el-button>
            <el-button
              v-if="isExternalPending(item)"
              type="success"
              link
              @click="markExternalPassed(item.chapter_id)"
            >
              外审已通过
            </el-button>
            <el-button
              v-if="isQualityBlocked(item)"
              type="danger"
              link
              @click="openUnifiedGate(item.chapter_id)"
            >
              统一门禁
            </el-button>
            <el-button
              type="primary"
              link
              :icon="CopyDocument"
              :loading="copyingId === item.chapter_id"
              @click="copyBodyForPlatform(item.chapter_id)"
            >
              复制试审
            </el-button>
            <el-button type="info" link @click="openUnifiedGate(item.chapter_id)">
              章节详情
            </el-button>
          </template>
          <template v-else>
            <el-button type="primary" link :icon="Edit" @click="openChapter(item.chapter_id)">
              {{ selectMode === 'emit' ? '打开本章' : '去写作台' }}
            </el-button>
            <el-button
              type="warning"
              link
              :icon="Refresh"
              :loading="resumingId === item.chapter_id"
              @click="resumeAudit(item.chapter_id)"
            >
              重试审校
            </el-button>
          </template>
          <el-button
            type="info"
            link
            :loading="dismissingId === item.chapter_id"
            @click="dismissAlert(item.chapter_id)"
          >
            已处理
          </el-button>
        </div>
      </li>
    </ul>

  </section>
</template>

<style scoped>
.pipeline-alerts-banner {
  border: 1px solid var(--color-alert-danger-border);
  border-radius: 10px;
  background: var(--color-alert-danger-bg);
  padding: 14px 16px;
  margin-bottom: 16px;
}

.banner-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.bulk-checkbox {
  margin-right: 2px;
}

.banner-icon {
  font-size: 22px;
  color: var(--color-danger);
}

.banner-title-area {
  flex: 1;
}

.banner-head strong {
  display: block;
  font-size: 15px;
  color: var(--color-text);
}

.banner-sub {
  display: block;
  font-size: 12px;
  color: var(--color-text-muted);
  font-weight: normal;
  margin-top: 2px;
}

.banner-audit-hint {
  margin: 0 0 12px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--color-text-muted);
}

.bulk-actions-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-alert-danger-border);
  padding: 10px 16px;
  border-radius: 8px;
  margin-bottom: 12px;
}

.selected-count {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
}

.bulk-buttons {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.bulk-progress-text {
  font-size: 12px;
  color: var(--color-primary);
  font-weight: 500;
}

.alert-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.alert-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-alert-danger-border);
  border-radius: 8px;
}

.alert-main {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.item-checkbox {
  margin-right: 4px;
}

.chapter-label {
  font-weight: 600;
  font-size: 13px;
  color: var(--color-text);
}

.chapter-label.clickable {
  cursor: pointer;
  color: var(--color-primary);
}

.chapter-label.clickable:hover {
  text-decoration: underline;
}

.alert-msg {
  font-size: 13px;
  color: #606266;
}

.alert-detail {
  font-size: 12px;
  color: #909399;
}

.alert-actions {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 4px;
}

/* Fade transition for bulk bar */
.fade-enter-active,
.fade-leave-active {
  transition: all 0.25s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>