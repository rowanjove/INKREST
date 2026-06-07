import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import { copyChapterPlainText } from '../utils/copyChapterText'
import { useChapterStore } from '../stores/chapter'
import {
  rerunChapterGate,
  resumeChapterAudit,
  rewriteChapter,
  setChapterExternalReview,
  updateChapter,
} from '../api'

export function parseChapterMarkdown(md: string) {
  if (!md) return ''
  let html = md.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  const lines = html.split('\n')
  const result: string[] = []
  let inList = false
  for (const line of lines) {
    const trimmed = line.trim()
    if (trimmed.startsWith('## ')) {
      if (inList) {
        result.push('</ul>')
        inList = false
      }
      result.push(`<h3 class="md-h3">${trimmed.substring(3)}</h3>`)
    } else if (trimmed.startsWith('# ')) {
      if (inList) {
        result.push('</ul>')
        inList = false
      }
      result.push(`<h2 class="md-h2">${trimmed.substring(2)}</h2>`)
    } else if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      if (!inList) {
        result.push('<ul class="md-ul">')
        inList = true
      }
      const itemText = trimmed.substring(2).replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      result.push(`<li class="md-li">${itemText}</li>`)
    } else if (trimmed === '') {
      if (inList) {
        result.push('</ul>')
        inList = false
      }
    } else {
      if (inList) {
        result.push('</ul>')
        inList = false
      }
      result.push(`<p class="md-p">${trimmed.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')}</p>`)
    }
  }
  if (inList) result.push('</ul>')
  return result.join('\n')
}

export function useChapterDetail() {
  const route = useRoute()
  const router = useRouter()
  const chapterStore = useChapterStore()
  const { currentChapter: chapter } = storeToRefs(chapterStore)

  const activeTab = ref('final')
  const loadError = ref('')
  const rewriting = ref(false)
  const resumingAudit = ref(false)
  const rerunningGate = ref(false)
  const externalStatus = ref<'none' | 'pending_external' | 'external_passed'>('none')
  const copying = ref(false)
  const editDialogVisible = ref(false)
  const savingEdit = ref(false)
  const editForm = ref({
    title: '',
    final_text: '',
  })

  const hasFinalText = computed(() => Boolean(chapter.value?.final_text?.trim()))

  const hasStateUpdates = computed(() => {
    const su = chapter.value?.state_update
    if (!su) return false
    return (
      (su.events?.length > 0) ||
      (su.timeline_nodes?.length > 0) ||
      (su.timeline_edges?.length > 0) ||
      (su.foreshadows?.length > 0) ||
      (su.hooks?.length > 0)
    )
  })

  const stateChangeCount = computed(() => {
    const su = chapter.value?.state_update
    if (!su) return 0
    return (su.events?.length || 0) + (su.timeline_nodes?.length || 0) + (su.foreshadows?.length || 0)
  })

  const isQualityBlocked = computed(() => {
    const cp = chapter.value?.checkpoint
    const gate = chapter.value?.unified_gate
    return cp?.last_stage === 'quality_blocked' || Boolean(gate?.blocked)
  })

  const resumableFrom = computed(() => {
    return chapter.value?.checkpoint?.resumable_from || chapter.value?.unified_gate?.resumable_from || ''
  })

  const wordStatusLabel = computed(() => {
    const count = chapter.value?.wordcount?.count || 0
    const status = chapter.value?.wordcount?.status
    if (!count || status === 'empty') return '空正文'
    if (status === 'under') return '字数不足'
    if (status === 'over') return '字数超出'
    if (status === 'ok') return '符合要求'
    return '未统计'
  })

  const startEdit = () => {
    if (!chapter.value) return
    editForm.value.title = chapter.value.title || ''
    editForm.value.final_text = chapter.value.final_text || ''
    editDialogVisible.value = true
  }

  const handleSaveEdit = async () => {
    if (!chapter.value?.chapter_id) return
    savingEdit.value = true
    try {
      await updateChapter(chapter.value.chapter_id, {
        title: editForm.value.title,
        final_text: editForm.value.final_text,
      })
      ElMessage.success('保存章节修改成功')
      editDialogVisible.value = false
      await chapterStore.fetchChapter(chapter.value.chapter_id)
    } catch (error: any) {
      ElMessage.error(error.message || '保存章节修改失败')
    } finally {
      savingEdit.value = false
    }
  }

  const handleCopyFullText = async () => {
    if (!chapter.value) return
    copying.value = true
    try {
      const len = await copyChapterPlainText({
        chapter_id: chapter.value.chapter_id,
        title: chapter.value.title,
        final_text: chapter.value.final_text,
      })
      ElMessage.success(`已复制全文（约 ${len} 字），可粘贴到网文平台`)
    } catch (error: any) {
      ElMessage.error(error?.message || '复制失败')
    } finally {
      copying.value = false
    }
  }

  const goWriter = () => {
    if (!chapter.value?.chapter_id) return
    router.push({ path: '/writer', query: { chapter: chapter.value.chapter_id } })
  }

  const handleRerunGate = async () => {
    if (!chapter.value?.chapter_id) return
    rerunningGate.value = true
    try {
      await rerunChapterGate(chapter.value.chapter_id)
      ElMessage.success('已提交只重跑门禁，请到章节维护查看')
    } catch (error: any) {
      ElMessage.error(error?.response?.data?.detail || error.message || '提交失败')
    } finally {
      rerunningGate.value = false
    }
  }

  const saveExternalStatus = async (status: 'none' | 'pending_external' | 'external_passed') => {
    if (!chapter.value?.chapter_id) return
    try {
      await setChapterExternalReview(chapter.value.chapter_id, { status })
      externalStatus.value = status
      ElMessage.success('外审状态已更新')
      await chapterStore.fetchChapter(chapter.value.chapter_id)
    } catch (error: any) {
      ElMessage.error(error?.response?.data?.detail || error.message || '保存失败')
    }
  }

  const handleResumeAudit = async () => {
    if (!chapter.value?.chapter_id) return
    resumingAudit.value = true
    try {
      await resumeChapterAudit(chapter.value.chapter_id)
      ElMessage.success('已提交重试审校，请到章节维护查看进度')
    } catch (error: any) {
      ElMessage.error(error?.response?.data?.detail || error.message || '提交失败')
    } finally {
      resumingAudit.value = false
    }
  }

  const openUnifiedGateTab = () => {
    activeTab.value = 'unified_gate'
  }

  const handleRewrite = async () => {
    if (!chapter.value?.chapter_id) return
    rewriting.value = true
    try {
      await rewriteChapter(chapter.value.chapter_id)
      ElMessage.success('重写任务已提交，可在日志中心查看任务流水')
    } catch (error: any) {
      ElMessage.error(error.message || '提交重写任务失败')
    } finally {
      rewriting.value = false
    }
  }

  const goBack = () => router.back()

  onMounted(async () => {
    const tab = route.query.tab
    if (typeof tab === 'string' && tab) {
      activeTab.value = tab === 'gate' ? 'unified_gate' : tab
    }
    try {
      await chapterStore.fetchChapter(route.params.id as string)
      const ext = (chapterStore.currentChapter as { external_review_status?: string } | null)
        ?.external_review_status
      if (ext === 'pending_external' || ext === 'external_passed') {
        externalStatus.value = ext
      } else {
        externalStatus.value = 'none'
      }
    } catch (error: any) {
      loadError.value = error.message || '章节加载失败'
    }
  })

  return {
    chapter,
    activeTab,
    loadError,
    rewriting,
    resumingAudit,
    rerunningGate,
    externalStatus,
    copying,
    editDialogVisible,
    savingEdit,
    editForm,
    hasFinalText,
    hasStateUpdates,
    stateChangeCount,
    isQualityBlocked,
    resumableFrom,
    wordStatusLabel,
    parseMarkdown: parseChapterMarkdown,
    startEdit,
    handleSaveEdit,
    handleCopyFullText,
    goWriter,
    handleRerunGate,
    saveExternalStatus,
    handleResumeAudit,
    openUnifiedGateTab,
    handleRewrite,
    goBack,
  }
}