import { ref, type ComputedRef, type Ref } from 'vue'
import { ElMessage } from 'element-plus'
import { storeToRefs } from 'pinia'
import { generateChapterPlan, runBatchChapters } from '../api'
import { buildChapterGoalTemplate } from '../utils/dashboardChapterGoal'
import { useChapterStore } from '../stores/chapter'
import { useProjectStore } from '../stores/project'

type BatchRow = { chapter_id: string; goal: string }

export function useDashboardBatchDialog(options: {
  outline: Ref<Record<string, any> | null>
  outlineTheme: ComputedRef<string>
  form: Ref<{ chapter_id: string; goal: string }>
}) {
  const { outline, outlineTheme, form } = options
  const chapterStore = useChapterStore()
  const projectStore = useProjectStore()
  const { currentProject } = storeToRefs(projectStore)

  const addChapterDialogVisible = ref(false)
  const addChapterTab = ref('single')
  const batchSubmitting = ref(false)
  const chapterPlanGenerating = ref(false)
  const batchInputMode = ref('list')
  const bulkText = ref('')
  const chapterPlanCount = ref(10)
  const chapterPlanInstructions = ref('')
  const batchRows = ref<BatchRow[]>([{ chapter_id: '001', goal: '' }])

  function chapterGoalTemplate(chapterId: string) {
    return buildChapterGoalTemplate({
      chapterId,
      outline: outline.value,
      outlineTheme: outlineTheme.value,
      projectName: currentProject.value?.name,
      projectDescription: currentProject.value?.description,
    })
  }

  function openAddChapterDialog() {
    if (!outline.value) {
      ElMessage.warning('请先在大纲页生成作品大纲')
      return
    }
    if (!outline.value.chosen_title) {
      ElMessage.warning('生成章节要求在大纲中确定小说最终名称')
      return
    }
    batchRows.value = [{ chapter_id: form.value.chapter_id || '001', goal: '' }]
    addChapterDialogVisible.value = true
    addChapterTab.value = 'single'
  }

  function addBatchRow() {
    const lastId = batchRows.value.at(-1)?.chapter_id || '000'
    const nextNum = Number.parseInt(lastId, 10) + 1
    batchRows.value.push({ chapter_id: String(nextNum).padStart(3, '0'), goal: '' })
  }

  function quickAddChapters(count: number) {
    if (
      batchRows.value.length === 1 &&
      batchRows.value[0].chapter_id.trim() &&
      !batchRows.value[0].goal.trim()
    ) {
      batchRows.value[0].goal = chapterGoalTemplate(batchRows.value[0].chapter_id)
      count -= 1
    }
    for (let i = 0; i < count; i++) {
      const lastId = batchRows.value.at(-1)?.chapter_id || '000'
      const nextNum = Number.parseInt(lastId, 10) + 1
      const chapter_id = String(nextNum).padStart(3, '0')
      batchRows.value.push({ chapter_id, goal: chapterGoalTemplate(chapter_id) })
    }
  }

  function clearBatchRows() {
    batchRows.value = [{ chapter_id: '001', goal: '' }]
  }

  function importFromBulkText() {
    const lines = bulkText.value.split('\n').map((l) => l.trim()).filter(Boolean)
    if (!lines.length) {
      ElMessage.warning('请输入有效的文本')
      return
    }

    let nextNum = 1
    if (batchRows.value.length) {
      const lastId = batchRows.value.at(-1)?.chapter_id || '000'
      nextNum = Number.parseInt(lastId, 10) + 1
    }

    let isFirstEmpty = batchRows.value.length === 1 && batchRows.value[0].goal.trim() === ''

    for (const line of lines) {
      if (isFirstEmpty) {
        batchRows.value[0].goal = line
        nextNum = Number.parseInt(batchRows.value[0].chapter_id, 10) + 1
        isFirstEmpty = false
      } else {
        batchRows.value.push({
          chapter_id: String(nextNum).padStart(3, '0'),
          goal: line,
        })
        nextNum++
      }
    }

    bulkText.value = ''
    batchInputMode.value = 'list'
    ElMessage.success(`成功解析并导入了 ${lines.length} 个章节目标`)
  }

  function removeBatchRow(index: number) {
    batchRows.value.splice(index, 1)
  }

  async function submitChapter() {
    if (!form.value.chapter_id.trim() || !form.value.goal.trim()) {
      ElMessage.warning('章节编号和章节目标都要填写')
      return
    }
    try {
      await chapterStore.submitChapter({ ...form.value, dry_run: false })
      ElMessage.success('章节任务已进入队列')
      addChapterDialogVisible.value = false
    } catch (error: any) {
      ElMessage.error(error.message || '任务提交失败')
    }
  }

  async function submitBatch() {
    const validRows = batchRows.value.filter((row) => row.chapter_id.trim() && row.goal.trim())
    if (validRows.length === 0) {
      ElMessage.warning('至少需要一个完整章节')
      return
    }
    batchSubmitting.value = true
    try {
      await runBatchChapters({ chapters: validRows, dry_run: false })
      ElMessage.success(`已提交 ${validRows.length} 个章节任务`)
      addChapterDialogVisible.value = false
      await chapterStore.fetchTasks()
    } catch (error: any) {
      ElMessage.error(error.message || '批量提交失败')
    } finally {
      batchSubmitting.value = false
    }
  }

  async function fillBatchFromAI() {
    if (!outline.value) {
      ElMessage.warning('请先在大纲页生成或保存作品大纲')
      return
    }
    chapterPlanGenerating.value = true
    try {
      const start =
        Number.parseInt(batchRows.value[0]?.chapter_id || form.value.chapter_id || '001', 10) || 1
      const { data } = await generateChapterPlan({
        start_chapter: start,
        count: chapterPlanCount.value,
        instructions: chapterPlanInstructions.value,
      })
      batchRows.value = (data.chapters || []).map((chapter: any) => ({
        chapter_id: chapter.chapter_id,
        goal: chapter.title ? `${chapter.title}：${chapter.goal}` : chapter.goal,
      }))
      const arcLabel = data.macro_arc_name || data.macro_arc_id
      const arcHint = arcLabel ? `（宏观卷：${arcLabel}）` : ''
      ElMessage.success(`已根据大纲生成 ${batchRows.value.length} 个章节目标${arcHint}`)
    } catch (error: any) {
      ElMessage.error(error?.response?.data?.detail || error.message || 'AI 拆章失败')
    } finally {
      chapterPlanGenerating.value = false
    }
  }

  return {
    addChapterDialogVisible,
    addChapterTab,
    batchSubmitting,
    chapterPlanGenerating,
    batchInputMode,
    bulkText,
    chapterPlanCount,
    chapterPlanInstructions,
    batchRows,
    openAddChapterDialog,
    addBatchRow,
    quickAddChapters,
    clearBatchRows,
    importFromBulkText,
    removeBatchRow,
    submitChapter,
    submitBatch,
    fillBatchFromAI,
  }
}