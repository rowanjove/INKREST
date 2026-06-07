<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CopyDocument, Delete, Edit, Plus, Search } from '@element-plus/icons-vue'
import { usePipelineAlertsStore } from '../stores/pipelineAlerts'
import { apiErrorMessage, deleteChapter, getArcProgress, getChapter, listChapters, rerunChapterGate, runChapter, suggestChapterGoal } from '../api'
import { isQualityBlocked } from '../utils/pipelineAlertFilters'
import { copyChapterTitleOnly, copyChapterBodyOnly } from '../utils/copyChapterText'
import { useTasksStore } from '../stores/tasks'

const router = useRouter()
const alertsStore = usePipelineAlertsStore()
const tasksStore = useTasksStore()
const { alerts: pipelineAlerts } = storeToRefs(alertsStore)
const chapters = ref<any[]>([])
const arcs = ref<any[]>([])
const arcProgress = ref<Record<string, any> | null>(null)
const deletingId = ref('')
const copyingId = ref('')
const gateRerunId = ref('')

const searchQuery = ref('')
const selectedStatus = ref('')
const currentPage = ref(1)
const pageSize = ref(10)

const repairDialogVisible = ref(false)
const repairForm = ref({
  chapter_id: '',
  goal: '',
})
const repairing = ref(false)
const suggestingGoal = ref(false)

const handleSuggestGoal = async () => {
  try {
    suggestingGoal.value = true
    const { data } = await suggestChapterGoal(repairForm.value.chapter_id)
    if (data && data.goal) {
      repairForm.value.goal = data.goal
      ElMessage.success(data.message || '已自动预测/引入大纲')
    }
  } catch (error: any) {
    ElMessage.error(apiErrorMessage(error, 'AI 预测失败'))
  } finally {
    suggestingGoal.value = false
  }
}

const goWriter = (chapterId: string) => {
  router.push({ path: '/writer', query: { chapter: chapterId } })
}

const pipelineAlertFor = (chapterId: string) =>
  pipelineAlerts.value.find((item) => item.chapter_id === chapterId)

const isGateBlockedChapter = (chapterId: string) => {
  const item = pipelineAlertFor(chapterId)
  return item ? isQualityBlocked(item) : false
}

const rerunGateOnly = async (chapterId: string) => {
  gateRerunId.value = chapterId
  try {
    await rerunChapterGate(chapterId)
    ElMessage.success(`第 ${chapterId} 章已提交重跑门禁`)
    await alertsStore.fetchAlerts()
  } catch (error: any) {
    ElMessage.error(apiErrorMessage(error, '提交失败'))
  } finally {
    gateRerunId.value = ''
  }
}

const loadChapters = async () => {
  try {
    const { data } = await listChapters({ offset: 0, limit: 500, sync: true, include_gaps: true })
    chapters.value = data.items ?? data
  } catch (error: any) {
    chapters.value = []
    ElMessage.error(apiErrorMessage(error, '加载章节列表失败'))
  }
  try {
    const arcRes = await getArcProgress()
    arcs.value = arcRes.data.arcs || []
    arcProgress.value = arcRes.data.progress || null
  } catch {
    arcs.value = []
    arcProgress.value = null
  }
}

const filteredChapters = computed(() => {
  const list = chapters.value.slice().sort((a, b) => String(b.chapter_id).localeCompare(String(a.chapter_id)))
  return list.filter((c) => {
    const nameMatch =
      c.chapter_id.includes(searchQuery.value) ||
      (c.title || '').toLowerCase().includes(searchQuery.value.toLowerCase())

    const isMissing = c.is_missing
    const statusMatch =
      !selectedStatus.value ||
      (selectedStatus.value === 'missing' && isMissing) ||
      (selectedStatus.value === 'done' && !isMissing && c.final_path) ||
      (selectedStatus.value === 'pending' && !isMissing && !c.final_path)

    return nameMatch && statusMatch
  })
})

const paginatedChapters = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredChapters.value.slice(start, end)
})

const openRepairDialog = (chapter: any) => {
  repairForm.value.chapter_id = chapter.chapter_id
  repairForm.value.goal = ''
  repairDialogVisible.value = true
}

const submitRepair = async () => {
  if (!repairForm.value.goal.trim()) {
    ElMessage.warning('请填写生成目标/写作大纲')
    return
  }
  try {
    repairing.value = true
    await runChapter({
      chapter_id: repairForm.value.chapter_id,
      goal: repairForm.value.goal.trim(),
      dry_run: false,
    })
    ElMessage.success(`章节 ${repairForm.value.chapter_id} 补齐任务已提交，请到章节维护查看`)
    repairDialogVisible.value = false
    await loadChapters()
  } catch (error: any) {
    ElMessage.error(apiErrorMessage(error, '提交失败'))
  } finally {
    repairing.value = false
  }
}

const copyChapterTitle = async (chapter: any) => {
  if (!chapter?.chapter_id || chapter.is_missing) return
  copyingId.value = chapter.chapter_id
  try {
    const { data } = await getChapter(chapter.chapter_id)
    const len = await copyChapterTitleOnly(data.title || chapter.title)
    ElMessage.success(`已复制标题（${len} 字）`)
  } catch (error: any) {
    ElMessage.error(apiErrorMessage(error, '复制失败'))
  } finally {
    copyingId.value = ''
  }
}

const copyChapterBody = async (chapter: any) => {
  if (!chapter?.chapter_id || chapter.is_missing) return
  copyingId.value = chapter.chapter_id
  try {
    const { data } = await getChapter(chapter.chapter_id)
    const len = await copyChapterBodyOnly(data.final_text)
    ElMessage.success(`已复制正文（约 ${len} 字）`)
  } catch (error: any) {
    ElMessage.error(apiErrorMessage(error, '复制失败'))
  } finally {
    copyingId.value = ''
  }
}

const confirmDelete = async (chapter: any) => {
  try {
    await ElMessageBox.confirm(
      `确定删除章节 ${chapter.chapter_id}？该章节正文、计划和报告都会移除。`,
      '删除章节',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      },
    )
    deletingId.value = chapter.chapter_id
    await deleteChapter(chapter.chapter_id)
    ElMessage.success(`章节 ${chapter.chapter_id} 已删除`)
    await loadChapters()
  } catch (error: any) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(apiErrorMessage(error, '删除失败'))
    }
  } finally {
    deletingId.value = ''
  }
}

const getRiskTagType = (chapter: any) => {
  if (chapter.is_missing) return 'danger'
  if (chapter.risk_level === '高') return 'danger'
  if (chapter.risk_level === '中') return 'warning'
  return 'success'
}

const refreshAlerts = () => {
  void alertsStore.fetchAlerts()
}

watch(
  () => tasksStore.isRunning,
  (running, wasRunning) => {
    if (wasRunning && !running) refreshAlerts()
  },
)

onMounted(async () => {
  await Promise.all([loadChapters(), alertsStore.fetchAlerts()])
})
</script>

<template>
  <section class="chapters-page">
    <div class="filter-bar panel">
      <el-input
        v-model="searchQuery"
        placeholder="输入章节ID或名称模糊搜索..."
        clearable
        :prefix-icon="Search"
        class="search-input"
        @input="currentPage = 1"
      />
      <el-select
        v-model="selectedStatus"
        placeholder="生产状态"
        clearable
        class="filter-select"
        @change="currentPage = 1"
      >
        <el-option label="缺失断档" value="missing" />
        <el-option label="正文已就绪" value="done" />
        <el-option label="等待正文生成" value="pending" />
      </el-select>
    </div>

    <el-alert
      v-if="pipelineAlerts.length > 0"
      type="warning"
      :closable="false"
      show-icon
      title="有章节待改稿"
      class="pending-alert"
    >
      共 {{ pipelineAlerts.length }} 章未过内部门禁。请先在章节维护或下方「编辑」处理，再回工作台继续写书。
      <el-button type="warning" link style="margin-left: 8px" @click="router.push('/chapters/maintenance')">
        打开章节维护
      </el-button>
    </el-alert>

    <div class="chapters-table-wrapper panel">
      <el-table
        v-loading="deletingId !== ''"
        :data="paginatedChapters"
        style="width: 100%"
        row-key="chapter_id"
        class="custom-chapters-table"
      >
        <el-table-column label="章节编号" width="120">
          <template #default="{ row }">
            <span class="ch-num-tag" :class="{ missing: row.is_missing }">
              {{ row.chapter_id }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="章节名称" min-width="200">
          <template #default="{ row }">
            <span v-if="row.is_missing" class="ch-title-text missing">【数据缺失断档】</span>
            <div v-else class="title-copy-row">
              <span
                class="ch-title-text clickable-title"
                @click="router.push(`/chapters/${row.chapter_id}`)"
              >
                {{ row.title || '未命名章节' }}
              </span>
              <el-button
                type="primary"
                link
                size="small"
                :icon="CopyDocument"
                :loading="copyingId === row.chapter_id"
                title="复制标题"
                aria-label="复制标题"
                class="copy-icon-only"
                @click.stop="copyChapterTitle(row)"
              />
            </div>
          </template>
        </el-table-column>

        <el-table-column label="字数" width="120">
          <template #default="{ row }">
            <span v-if="!row.is_missing" class="wordcount-text">{{ row.word_count || 0 }} 字</span>
            <span v-else class="wordcount-text missing">—</span>
          </template>
        </el-table-column>

        <el-table-column label="审核风险" width="120">
          <template #default="{ row }">
            <el-tag size="small" :type="getRiskTagType(row)">
              {{ row.is_missing ? '待补齐' : (row.risk_level || '未审核') }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="生产状态" width="160">
          <template #default="{ row }">
            <span v-if="row.is_missing" class="state-txt missing">缺失断档</span>
            <span v-else-if="row.final_path" class="state-txt ready">正文已生成</span>
            <span v-else class="state-txt pending">等待正文</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="260" align="right">
          <template #default="{ row }">
            <div class="action-buttons-wrap">
              <template v-if="!row.is_missing">
                <el-button
                  v-if="isGateBlockedChapter(row.chapter_id)"
                  size="small"
                  type="warning"
                  plain
                  :loading="gateRerunId === row.chapter_id"
                  @click="rerunGateOnly(row.chapter_id)"
                >
                  只重跑门禁
                </el-button>
                <el-button
                  class="chapter-edit-btn"
                  size="small"
                  type="primary"
                  plain
                  :icon="Edit"
                  @click="goWriter(row.chapter_id)"
                >
                  编辑
                </el-button>
                <el-button
                  size="small"
                  plain
                  :icon="CopyDocument"
                  :loading="copyingId === row.chapter_id"
                  title="复制正文"
                  @click="copyChapterBody(row)"
                >
                  复制
                </el-button>
                <el-button
                  size="small"
                  type="danger"
                  plain
                  :icon="Delete"
                  :loading="deletingId === row.chapter_id"
                  :disabled="tasksStore.isRunning"
                  @click="confirmDelete(row)"
                >
                  删除
                </el-button>
              </template>
              <template v-else>
                <el-button size="small" type="primary" :icon="Plus" :disabled="tasksStore.isRunning" @click="openRepairDialog(row)">
                  补齐流水线
                </el-button>
              </template>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-bar" v-if="filteredChapters.length > 0">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="filteredChapters.length"
        />
      </div>
      <div v-else-if="chapters.length > 0" class="no-results-alert">暂无符合筛选条件的章节</div>
      <div v-else class="empty-list-card">
        <h2>还没有章节数据</h2>
        <p>请在侧栏进入「工作台」启动「连写启动」后，此处会展示各章进度。</p>
      </div>
    </div>

    <el-dialog v-model="repairDialogVisible" :title="`补齐 ${repairForm.chapter_id}`" width="500px">
      <el-form :model="repairForm" label-position="top">
        <el-form-item required>
          <template #label>
            <div style="display: flex; justify-content: space-between; align-items: center; width: 100%">
              <span>本章写作目标 (Goal)</span>
              <el-button type="primary" link :loading="suggestingGoal" :disabled="tasksStore.isRunning || suggestingGoal" @click="handleSuggestGoal">
                AI 读入大纲
              </el-button>
            </div>
          </template>
          <el-input
            v-model="repairForm.goal"
            type="textarea"
            :rows="5"
            placeholder="描述该章发展脉络或写作要求"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="repairDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="repairing" :disabled="tasksStore.isRunning || repairing" @click="submitRepair">运行章节流水线</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.chapters-page {
  display: grid;
  gap: 20px;
}

.pending-alert {
  margin: 0;
}

.filter-bar {
  display: flex;
  gap: 12px;
  padding: 16px;
  align-items: center;
}

.search-input {
  flex: 1;
}

.filter-select {
  width: 200px;
}

.arc-panel {
  padding: 20px 24px;
  border-radius: 12px;
  border: 1px solid var(--color-border, #e2e8f0);
  background: var(--color-bg-surface, #fff);
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05);
}

.arc-panel-header {
  border-bottom: 1px solid var(--color-border-subtle, #f1f5f9);
  padding-bottom: 14px;
  margin-bottom: 16px;
}

.arc-panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 6px;
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-strong, #0f172a);
}

.title-icon-main {
  color: #ea580c;
}

.arc-panel-hint {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-muted, #64748b);
  line-height: 1.5;
}

.arc-panel-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  gap: 24px;
  align-items: stretch;
}

@media (max-width: 900px) {
  .arc-panel-grid {
    grid-template-columns: 1fr;
  }
}

.arc-panel-main {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 16px;
}

.status-badge-container {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.status-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-muted, #64748b);
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 9999px;
  font-size: 13px;
  font-weight: 600;
  line-height: 1;
}

/* Base states for status badge */
.status-badge.running {
  background-color: #ecfdf5;
  color: #059669;
  border: 1px solid #a7f3d0;
}

.status-badge.paused {
  background-color: #fff7ed;
  color: #d97706;
  border: 1px solid #ffedd5;
}

.status-badge.completed {
  background-color: #eff6ff;
  color: #2563eb;
  border: 1px solid #bfdbfe;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #10b981;
  animation: pulse-animation 1.5s infinite;
}

@keyframes pulse-animation {
  0% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
  }
  70% {
    transform: scale(1);
    box-shadow: 0 0 0 6px rgba(16, 185, 129, 0);
  }
  100% {
    transform: scale(0.95);
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
  }
}

.status-text {
  font-size: 12px;
  font-weight: 500;
  opacity: 0.9;
}

.resume-action-btn {
  margin-left: 4px;
  height: 28px;
  padding: 0 12px;
  font-size: 12px;
  border-radius: 9999px;
}

.arc-chips-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-sub-title {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-muted, #94a3b8);
}

.arc-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.custom-arc-tag {
  height: 28px;
  padding: 0 10px;
  border-radius: 6px;
  border-color: #cbd5e1;
  background-color: #f1f5f9;
  color: #334155;
  display: flex;
  align-items: center;
  font-weight: 500;
  font-size: 13px;
}

.arc-tag-id {
  font-family: monospace;
  font-weight: 700;
  color: #475569;
}

.arc-tag-divider {
  margin: 0 6px;
  opacity: 0.3;
}

.arc-tag-count {
  color: #64748b;
}

.arc-panel-side-clean {
  display: flex;
  flex-direction: column;
  justify-content: stretch;
}

.chapters-table-wrapper {
  padding: 12px 18px;
}

.custom-chapters-table {
  --el-table-border-color: var(--color-bg-hover);
  --el-table-header-bg-color: var(--color-bg-surface-muted);
}

.ch-num-tag {
  font-family: monospace;
  font-weight: 700;
  color: #b66346;
  font-size: 14.5px;
}

.ch-num-tag.missing {
  color: var(--color-danger);
}

.title-copy-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.ch-title-text {
  font-weight: 600;
  color: var(--color-text-strong);
}

.ch-title-text.clickable-title {
  cursor: pointer;
  color: var(--primary);
}

.ch-title-text.clickable-title:hover {
  text-decoration: underline;
}

.ch-title-text.missing {
  color: var(--color-text-subtle);
  font-style: italic;
  font-weight: 400;
}

.wordcount-text {
  font-size: 13.5px;
  color: #4b5563;
}

.wordcount-text.missing {
  color: var(--color-border);
}

.state-txt {
  font-size: 13px;
  font-weight: 600;
}

.state-txt.missing {
  color: #f87171;
}

.state-txt.ready {
  color: var(--color-success);
}

.state-txt.pending {
  color: var(--color-warning);
}

.action-buttons-wrap {
  display: flex;
  gap: 6px;
  justify-content: flex-end;
}

.chapter-edit-btn.el-button--primary.is-plain {
  font-weight: 700;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 14px;
  border-top: 1px solid var(--color-border-subtle);
}

.no-results-alert {
  padding: 30px;
  text-align: center;
  color: var(--text-muted);
  font-size: 14px;
}

.empty-list-card {
  display: grid;
  place-items: start;
  gap: 10px;
  padding: 34px;
}

.empty-list-card h2,
.empty-list-card p {
  margin: 0;
}
</style>
