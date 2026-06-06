<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowDown,
  CopyDocument,
  Edit,
  Refresh,
  Warning,
} from '@element-plus/icons-vue'
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
import { pendingPanelExpanded } from '../composables/usePendingPanelExpand'
import { usePipelineAlertsStore } from '../stores/pipelineAlerts'
import { copyChapterPlainText } from '../utils/copyChapterText'
import {
  canRerunAudit,
  isExternalPending,
  isQualityBlocked,
  needsRepairActions,
  PENDING_STEP_CARDS,
} from '../utils/pipelineAlertFilters'
import { DUAL_AUDIT_HINT } from '../constants/repairWorkflow'
import { useRepairChapterFocus } from '../composables/useRepairChapterFocus'

const props = withDefaults(
  defineProps<{
    pollIntervalMs?: number
    showActions?: boolean
    selectMode?: 'navigate' | 'emit'
    hideFootnote?: boolean
    linkFocus?: boolean
  }>(),
  {
    pollIntervalMs: 4000,
    showActions: true,
    selectMode: 'navigate',
    hideFootnote: false,
    linkFocus: false,
  },
)

const { setFocusedChapter } = useRepairChapterFocus()

const emit = defineEmits<{
  selectChapter: [chapterId: string]
}>()

const router = useRouter()
const alertsStore = usePipelineAlertsStore()
const { pipelineAlerts } = usePipelineAlerts(props.pollIntervalMs)

const expanded = pendingPanelExpanded
const selectedIds = ref<string[]>([])
const isProcessingBulk = ref(false)
const bulkProgress = ref({ current: 0, total: 0 })
const resumingId = ref<string | null>(null)
const gateRerunId = ref<string | null>(null)
const dismissingId = ref<string | null>(null)
const copyingId = ref<string | null>(null)
const activeCardId = ref<string | null>(null)

const totalCount = computed(() => pipelineAlerts.value.length)

const stepViews = computed(() =>
  PENDING_STEP_CARDS.map((card) => ({
    ...card,
    count: pipelineAlerts.value.filter((item) => card.filter(item)).length,
    targets: pipelineAlerts.value
      .filter((item) => card.filter(item))
      .map((item) => item.chapter_id),
  })),
)

const isAllSelected = computed(
  () =>
    pipelineAlerts.value.length > 0 &&
    selectedIds.value.length === pipelineAlerts.value.length,
)

const isIndeterminate = computed(
  () =>
    selectedIds.value.length > 0 &&
    selectedIds.value.length < pipelineAlerts.value.length,
)

watch(pipelineAlerts, (newAlerts) => {
  const currentIds = newAlerts.map((item) => item.chapter_id)
  selectedIds.value = selectedIds.value.filter((id) => currentIds.includes(id))
}, { deep: true })

const toggleExpanded = () => {
  expanded.value = !expanded.value
}

const toggleSelectAll = (val: boolean) => {
  selectedIds.value = val ? pipelineAlerts.value.map((item) => item.chapter_id) : []
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

const resolveTargets = (explicit: string[]) => {
  if (selectedIds.value.length > 0) {
    return selectedIds.value.filter((id) => explicit.includes(id))
  }
  return explicit
}

const runBatchTask = async (
  actionName: string,
  targets: string[],
  actionFn: (id: string) => Promise<unknown>,
) => {
  if (targets.length === 0) {
    ElMessage.info('当前步骤没有可处理的章节')
    return
  }

  isProcessingBulk.value = true
  bulkProgress.value = { current: 0, total: targets.length }
  let successCount = 0
  let failCount = 0
  const errors: string[] = []

  await Promise.all(
    targets.map(async (id) => {
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
    }),
  )

  if (successCount > 0) {
    ElMessage.success(`成功对 ${successCount} 个章节执行「${actionName}」`)
  }
  if (failCount > 0) {
    ElMessage.error(`${failCount} 个章节失败:\n${errors.join('\n')}`)
  }

  selectedIds.value = selectedIds.value.filter((id) => !targets.includes(id))
  isProcessingBulk.value = false
  await alertsStore.fetchAlerts()
}

const bulkResumeAudit = async (targets: string[]) => {
  await runBatchTask('重试审校', targets, resumeChapterAudit)
}

const bulkRerunGate = async (targets: string[]) => {
  await runBatchTask(
    '重跑门禁',
    targets.filter((id) => {
      const item = pipelineAlerts.value.find((a) => a.chapter_id === id)
      return item && !isExternalPending(item)
    }),
    rerunChapterGate,
  )
}

const bulkExternalPassed = async (targets: string[]) => {
  await runBatchTask(
    '外审已通过',
    targets.filter((id) => {
      const item = pipelineAlerts.value.find((a) => a.chapter_id === id)
      return item && isExternalPending(item)
    }),
    (id) => setChapterExternalReview(id, { status: 'external_passed' }),
  )
}

const handleRewriteBatch = async (targets: string[]) => {
  const resolved = resolveTargets(targets)
  if (resolved.length === 0) {
    ElMessage.info('当前没有可重跑的章节')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定批量重跑 ${resolved.length} 个章节吗？将清空断点并按最新方案从头重写。`,
      '批量重跑确认',
      { confirmButtonText: '确定重跑', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }

  isProcessingBulk.value = true
  bulkProgress.value = { current: 0, total: resolved.length }
  try {
    const { data } = await rewriteBatchChapters(resolved)
    ElMessage.success(`已提交批量重跑，批次 ID: ${data.batch_id}`)
    selectedIds.value = selectedIds.value.filter((id) => !resolved.includes(id))
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error.message || '批量重跑提交失败')
  } finally {
    isProcessingBulk.value = false
    await alertsStore.fetchAlerts()
  }
}

const runCardBulk = async (cardId: string) => {
  const card = stepViews.value.find((c) => c.id === cardId)
  if (!card || card.count === 0) return

  activeCardId.value = cardId
  const targets = resolveTargets(card.targets)

  try {
    switch (card.bulkAction) {
      case 'resume-audit':
        await bulkResumeAudit(targets)
        break
      case 'rerun-gate':
        await bulkRerunGate(targets)
        break
      case 'external-passed':
        await bulkExternalPassed(targets)
        break
      case 'rewrite-batch':
        await handleRewriteBatch(card.targets)
        break
    }
  } finally {
    activeCardId.value = null
  }
}

const copyBodyForPlatform = async (chapterId: string) => {
  copyingId.value = chapterId
  try {
    const { data } = await getChapter(chapterId)
    const len = await copyChapterPlainText({
      chapter_id: data.chapter_id,
      title: data.title,
      final_text: data.final_text,
    })
    ElMessage.success(`已复制第 ${chapterId} 章全文（约 ${len} 字）`)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error.message || '复制失败')
  } finally {
    copyingId.value = null
  }
}

const focusChapter = (chapterId: string) => {
  if (props.linkFocus) {
    setFocusedChapter(chapterId)
  }
}

const openChapter = (chapterId: string) => {
  focusChapter(chapterId)
  if (props.selectMode === 'emit') {
    emit('selectChapter', chapterId)
    return
  }
  router.push({ path: '/writer', query: { chapter: chapterId } })
}

const openUnifiedGate = (chapterId: string) => {
  router.push({ path: `/chapters/${chapterId}`, query: { tab: 'unified_gate' } })
}

const dismissAlert = async (chapterId: string) => {
  dismissingId.value = chapterId
  try {
    await dismissPipelineAlert(chapterId)
    ElMessage.success(`第 ${chapterId} 章已标记为已处理`)
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
    ElMessage.success(`第 ${chapterId} 章已提交重跑门禁`)
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
    ElMessage.success(`第 ${chapterId} 章已提交重试审校`)
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
    id="pipeline-alerts-section"
    class="pipeline-panel pipeline-panel--alert"
    :class="{ 'pipeline-panel--has-items': totalCount > 0 }"
  >
    <button
      type="button"
      class="pipeline-panel__head pipeline-panel__head--toggle"
      @click="toggleExpanded"
    >
      <el-icon
        class="pipeline-panel__head-icon"
        :class="{ 'pipeline-panel__head-icon--warn': totalCount > 0 }"
      >
        <Warning />
      </el-icon>
      <div class="pipeline-panel__head-copy">
        <h2 class="pipeline-panel__title">修章队列</h2>
        <span class="pipeline-panel__hint">
          {{
            totalCount > 0
              ? '按门禁阻断 → 批量跳过 → 待外审分组处理'
              : '暂无待处理章节'
          }}
        </span>
      </div>
      <el-tag
        class="pipeline-panel__meta"
        :type="totalCount > 0 ? 'danger' : 'info'"
        size="small"
        effect="plain"
      >
        {{ totalCount }} 章
      </el-tag>
      <el-icon
        class="pipeline-panel__chevron"
        :class="{ 'pipeline-panel__chevron--open': expanded }"
      >
        <ArrowDown />
      </el-icon>
    </button>

    <div class="pipeline-stage-grid pipeline-stage-grid--cols-4 pipeline-stage-grid--bordered">
      <article
        v-for="card in stepViews"
        :key="card.id"
        class="pipeline-stage-card"
        :class="{
          'pipeline-stage-card--has-count': card.count > 0,
          'pipeline-stage-card--active': activeCardId === card.id,
        }"
      >
        <div class="pipeline-stage-top">
          <span class="pipeline-stage-index">S{{ card.index }}</span>
          <strong
            class="pipeline-stage-count"
            :class="{ 'pipeline-stage-count--zero': card.count === 0 }"
          >
            {{ card.count }}
          </strong>
        </div>
        <strong class="pipeline-stage-label">{{ card.label }}</strong>
        <p class="pipeline-stage-desc">{{ card.desc }}</p>
        <div v-if="card.bulkAction" class="pipeline-stage-actions">
          <el-button
            size="small"
            type="primary"
            plain
            :disabled="card.count === 0 || isProcessingBulk"
            :loading="isProcessingBulk && activeCardId === card.id"
            @click.stop="runCardBulk(card.id)"
          >
            批量处理
          </el-button>
        </div>
      </article>
    </div>

    <p v-if="!hideFootnote" class="pipeline-panel__footnote">{{ DUAL_AUDIT_HINT }}</p>

    <div v-show="expanded" class="pipeline-panel__body">
      <div v-if="selectedIds.length > 0" class="bulk-bar">
        <span>已选 {{ selectedIds.length }} 章</span>
        <div class="bulk-bar-actions">
          <el-button
            size="small"
            type="warning"
            :loading="isProcessingBulk"
            @click="bulkResumeAudit(selectedIds)"
          >
            批量重试审校
          </el-button>
          <el-button
            size="small"
            type="success"
            :loading="isProcessingBulk"
            @click="bulkRerunGate(selectedIds)"
          >
            批量重跑门禁
          </el-button>
          <el-button
            size="small"
            type="success"
            :loading="isProcessingBulk"
            @click="bulkExternalPassed(selectedIds)"
          >
            批量外审通过
          </el-button>
        </div>
      </div>

      <div v-if="isProcessingBulk" class="bulk-progress">
        处理中… {{ bulkProgress.current }} / {{ bulkProgress.total }}
      </div>

      <div v-if="totalCount === 0" class="empty-list">
        当前没有待处理章节。连写正常时此处各步骤计数为 0。
      </div>

      <ul v-else class="chapter-list">
        <li v-for="item in pipelineAlerts" :key="item.chapter_id" class="chapter-row">
          <div class="row-main">
            <el-checkbox
              :model-value="selectedIds.includes(item.chapter_id)"
              @change="(val: boolean) => handleCheckboxChange(item.chapter_id, val)"
            />
            <el-tag type="danger" size="small" effect="plain">
              {{ formatAlertStage(item.last_stage) }}
            </el-tag>
            <span
              class="chapter-id"
              :class="{ 'chapter-id--focusable': linkFocus }"
              @click="focusChapter(item.chapter_id)"
            >
              第 {{ item.chapter_id }} 章
            </span>
            <span class="chapter-msg">{{ item.message }}</span>
            <span v-if="item.quality?.blocked_by?.length" class="chapter-detail">
              阻断: {{ item.quality.blocked_by.join(', ') }}
            </span>
          </div>
          <div v-if="showActions" class="row-actions">
            <template v-if="needsRepairActions(item)">
              <el-button type="info" link :icon="Edit" @click="openChapter(item.chapter_id)">
                改稿
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
                v-if="canRerunAudit(item)"
                type="success"
                link
                :loading="gateRerunId === item.chapter_id"
                @click="rerunGate(item.chapter_id)"
              >
                重跑门禁
              </el-button>
              <el-button
                v-if="isExternalPending(item)"
                type="success"
                link
                @click="markExternalPassed(item.chapter_id)"
              >
                外审通过
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

      <div v-if="totalCount > 0" class="list-toolbar">
        <el-checkbox
          :model-value="isAllSelected"
          :indeterminate="isIndeterminate"
          @change="toggleSelectAll"
        >
          全选
        </el-checkbox>
      </div>
    </div>
  </section>
</template>

<style scoped>
.bulk-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 10px;
  padding: 8px 12px;
  border-radius: 8px;
  background: var(--color-bg-surface-muted);
  border: 1px solid var(--color-border-subtle);
  font-size: 13px;
  font-weight: 600;
}

.bulk-bar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.bulk-progress {
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--color-primary);
}

.empty-list {
  padding: 20px 8px;
  text-align: center;
  font-size: 13px;
  color: var(--color-text-muted);
}

.chapter-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chapter-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--color-border-subtle);
  border-radius: 8px;
  background: var(--color-bg-surface-muted);
}

.row-main {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.chapter-id {
  font-weight: 700;
  font-size: 13px;
}

.chapter-id--focusable {
  cursor: pointer;
  color: var(--color-primary);
}

.chapter-id--focusable:hover {
  text-decoration: underline;
}

.chapter-msg {
  font-size: 12.5px;
  color: var(--color-text-muted);
}

.chapter-detail {
  font-size: 12px;
  color: var(--color-text-subtle);
}

.row-actions {
  display: flex;
  flex-shrink: 0;
  flex-wrap: wrap;
  gap: 2px;
}

.list-toolbar {
  margin-top: 10px;
}

@media (max-width: 720px) {
  .chapter-row {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>