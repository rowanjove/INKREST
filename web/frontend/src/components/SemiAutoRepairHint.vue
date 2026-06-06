<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowDown,
  CircleCheck,
  CopyDocument,
  Edit,
  Lightning,
  Refresh,
  Right,
} from '@element-plus/icons-vue'
import { getChapter, getNovelReadiness } from '../api'
import { usePipelineAlerts, formatAlertStage } from '../composables/usePipelineAlerts'
import { useNovelBatchRun } from '../composables/useNovelBatchRun'
import { useRepairChapterFocus } from '../composables/useRepairChapterFocus'
import { expandPendingPanel } from '../composables/usePendingPanelExpand'
import { copyChapterPlainText } from '../utils/copyChapterText'
import {
  DUAL_AUDIT_HINT,
  SEMI_AUTO_REPAIR_STEPS,
  type SemiAutoRepairAction,
} from '../constants/repairWorkflow'

const props = withDefaults(
  defineProps<{
    compact?: boolean
  }>(),
  { compact: false },
)

const panelHint = computed(() =>
  props.compact
    ? '选定本次修章后，按步骤改稿、复制试审并续跑批量。'
    : DUAL_AUDIT_HINT,
)

const router = useRouter()
const { pipelineAlerts } = usePipelineAlerts(4000)
const { openDialog } = useNovelBatchRun()
const {
  focusedChapterId,
  pickerVisible,
  setFocusedChapter,
  openPicker,
  closePicker,
} = useRepairChapterFocus(pipelineAlerts)

const activeStepId = ref<string | null>(null)
const copying = ref(false)

const hasAlerts = computed(() => pipelineAlerts.value.length > 0)
const pendingCount = computed(() => pipelineAlerts.value.length)

const focusLabel = computed(() => {
  if (!focusedChapterId.value) return '点击选择章节'
  const item = pipelineAlerts.value.find((a) => a.chapter_id === focusedChapterId.value)
  const stage = item ? formatAlertStage(item.last_stage) : ''
  return stage ? `第 ${focusedChapterId.value} 章 · ${stage}` : `第 ${focusedChapterId.value} 章`
})

const stepIcon = (action: SemiAutoRepairAction) => {
  switch (action) {
    case 'scroll-alerts':
      return Right
    case 'open-writer':
      return Edit
    case 'copy-trial':
      return CopyDocument
    case 'open-gate':
      return Refresh
    case 'continue-batch':
      return Lightning
    default:
      return Right
  }
}

const requireFocus = () => {
  if (focusedChapterId.value) return focusedChapterId.value
  if (hasAlerts.value) {
    openPicker()
    ElMessage.info('请先选择本次要处理的章节')
  } else {
    ElMessage.info('当前没有待处理章节')
  }
  return null
}

const openWriter = () => {
  const ch = requireFocus()
  if (!ch) return
  router.push({ path: '/writer', query: { chapter: ch } })
}

const copyTrial = async () => {
  const ch = requireFocus()
  if (!ch) return
  copying.value = true
  try {
    const { data } = await getChapter(ch)
    const len = await copyChapterPlainText({
      chapter_id: data.chapter_id,
      title: data.title,
      final_text: data.final_text,
    })
    ElMessage.success(`已复制第 ${ch} 章全文（约 ${len} 字），可粘贴到网文平台试审`)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error.message || '复制失败')
  } finally {
    copying.value = false
  }
}

const openGate = () => {
  const ch = requireFocus()
  if (!ch) return
  router.push({ path: `/chapters/${ch}`, query: { tab: 'unified_gate' } })
}

const continueBatch = async () => {
  if (hasAlerts.value) {
    ElMessage.warning('请先处理待处理章节，再续跑批量')
    await expandPendingPanel()
    return
  }
  try {
    const { data } = await getNovelReadiness()
    if (!data?.ok) {
      const labels = (data?.pending || []).map((item: { label?: string }) => item.label).filter(Boolean)
      ElMessage.warning(
        labels.length
          ? `开书清单未全绿：${labels.join('、')}。请先到工作台补齐。`
          : '开书清单未全绿，请先到工作台补齐后再续跑。',
      )
      router.push('/workspace')
      return
    }
  } catch {
    /* 非阻断，交给 openDialog 二次校验 */
  }
  await openDialog()
}

const handleStep = async (stepId: string, action: SemiAutoRepairAction) => {
  activeStepId.value = stepId
  try {
    switch (action) {
      case 'scroll-alerts':
        await expandPendingPanel()
        break
      case 'open-writer':
        openWriter()
        break
      case 'copy-trial':
        await copyTrial()
        break
      case 'open-gate':
        openGate()
        break
      case 'continue-batch':
        await continueBatch()
        break
    }
  } finally {
    window.setTimeout(() => {
      if (activeStepId.value === stepId) activeStepId.value = null
    }, 400)
  }
}

const stepDisabled = (action: SemiAutoRepairAction) => {
  if (action === 'copy-trial') return copying.value
  if (action === 'continue-batch') return false
  if (['open-writer', 'copy-trial', 'open-gate'].includes(action)) {
    return !hasAlerts.value
  }
  return false
}

const confirmPicker = () => {
  if (!focusedChapterId.value && pipelineAlerts.value.length > 0) {
    setFocusedChapter(pipelineAlerts.value[0].chapter_id)
  }
  closePicker()
}
</script>

<template>
  <section class="pipeline-panel">
    <el-alert
      v-if="hasAlerts"
      type="warning"
      :closable="false"
      show-icon
      class="repair-block-alert"
      :title="`请先处理 ${pendingCount} 章待改，再续跑连写`"
    >
      <el-button size="small" type="warning" plain @click="expandPendingPanel">
        展开修章队列
      </el-button>
    </el-alert>
    <div class="pipeline-panel__head">
      <div class="pipeline-panel__head-copy">
        <h2 class="pipeline-panel__title">半自动修章（外站审核友好）</h2>
        <span class="pipeline-panel__hint">{{ panelHint }}</span>
      </div>
      <button
        type="button"
        class="pipeline-panel__focus-picker pipeline-panel__meta"
        :disabled="!hasAlerts"
        @click="openPicker"
      >
        <span class="pipeline-panel__focus-label">本次修章</span>
        <strong class="pipeline-panel__focus-value">{{ focusLabel }}</strong>
        <el-icon class="pipeline-panel__chevron"><ArrowDown /></el-icon>
      </button>
    </div>

    <div class="pipeline-stage-grid pipeline-stage-grid--cols-5">
      <button
        v-for="(step, index) in SEMI_AUTO_REPAIR_STEPS"
        :key="step.id"
        type="button"
        class="pipeline-stage-card pipeline-stage-card--clickable"
        :class="{
          'pipeline-stage-card--active': activeStepId === step.id,
          'pipeline-stage-card--attention': step.action === 'scroll-alerts' && hasAlerts,
        }"
        :disabled="stepDisabled(step.action)"
        @click="handleStep(step.id, step.action)"
      >
        <div class="pipeline-stage-top">
          <span class="pipeline-stage-index">S{{ index + 1 }}</span>
          <el-icon v-if="step.action === 'copy-trial' && copying" class="is-loading">
            <Refresh />
          </el-icon>
          <el-icon v-else-if="step.action === 'continue-batch' && !hasAlerts">
            <CircleCheck />
          </el-icon>
        </div>
        <div class="pipeline-stage-icon-row">
          <el-icon><component :is="stepIcon(step.action)" /></el-icon>
          <strong>{{ step.label }}</strong>
        </div>
        <p class="pipeline-stage-desc">{{ step.desc }}</p>
        <span class="pipeline-stage-cta">点击执行</span>
      </button>
    </div>

    <el-dialog
      v-model="pickerVisible"
      title="选择本次要处理的章节"
      width="480px"
      append-to-body
      @closed="confirmPicker"
    >
      <p class="picker-hint">半自动修章的改稿、复制试审、查门禁等操作将针对所选章节执行。</p>
      <el-radio-group v-if="pipelineAlerts.length" v-model="focusedChapterId" class="picker-list">
        <el-radio
          v-for="item in pipelineAlerts"
          :key="item.chapter_id"
          :value="item.chapter_id"
          class="picker-item"
        >
          <span class="picker-ch">第 {{ item.chapter_id }} 章</span>
          <el-tag size="small" type="danger" effect="plain">
            {{ formatAlertStage(item.last_stage) }}
          </el-tag>
          <span class="picker-msg">{{ item.message }}</span>
        </el-radio>
      </el-radio-group>
      <el-empty v-else description="暂无待处理章节" :image-size="64" />
      <template #footer>
        <el-button @click="closePicker">取消</el-button>
        <el-button type="primary" :disabled="!focusedChapterId" @click="confirmPicker">
          确定
        </el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.repair-block-alert {
  margin-bottom: 12px;
}

.picker-hint {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--color-text-muted);
  line-height: 1.5;
}

.picker-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
  max-height: 360px;
  overflow-y: auto;
}

.picker-item {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  width: 100%;
  margin-right: 0;
  padding: 10px 12px;
  border: 1px solid var(--color-border-subtle);
  border-radius: 8px;
  height: auto;
}

.picker-item :deep(.el-radio__label) {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  width: 100%;
  white-space: normal;
}

.picker-ch {
  font-weight: 700;
  font-size: 13px;
}

.picker-msg {
  flex: 1 1 100%;
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.4;
}
</style>