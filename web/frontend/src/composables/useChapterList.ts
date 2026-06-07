import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { ElMessage, ElMessageBox } from 'element-plus'
import { usePipelineAlertsStore } from '../stores/pipelineAlerts'
import {
  apiErrorMessage,
  deleteChapter,
  getArcProgress,
  getChapter,
  listChapters,
  rerunChapterGate,
  runChapter,
  suggestChapterGoal,
} from '../api'
import { isQualityBlocked } from '../utils/pipelineAlertFilters'
import { copyChapterTitleOnly, copyChapterBodyOnly } from '../utils/copyChapterText'
import { useTasksStore } from '../stores/tasks'

export function useChapterList() {
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
    const list = chapters.value
      .slice()
      .sort((a, b) => String(b.chapter_id).localeCompare(String(a.chapter_id)))
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

  return {
    router,
    tasksStore,
    pipelineAlerts,
    chapters,
    arcs,
    arcProgress,
    deletingId,
    copyingId,
    gateRerunId,
    searchQuery,
    selectedStatus,
    currentPage,
    pageSize,
    repairDialogVisible,
    repairForm,
    repairing,
    suggestingGoal,
    filteredChapters,
    paginatedChapters,
    handleSuggestGoal,
    goWriter,
    isGateBlockedChapter,
    rerunGateOnly,
    openRepairDialog,
    submitRepair,
    copyChapterTitle,
    copyChapterBody,
    confirmDelete,
    getRiskTagType,
  }
}