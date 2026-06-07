import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { storeToRefs } from 'pinia'
import {
  adaptiveRewriteOutline,
  applyAdaptiveOutline,
  approveAllProjectCandidates,
  exportChaptersTrial,
  exportSerial,
  getNovelProgressSummary,
  getProjectComments,
  getProjectStateCandidates,
  getSerialStatus,
} from '../api'
import { copyPlainTextToClipboard } from '../utils/copyChapterText'
import { useProjectStore } from '../stores/project'

export function useDashboardSerial() {
  const projectStore = useProjectStore()
  const { currentProject } = storeToRefs(projectStore)

  const serialStatus = ref({
    today_word_count: 0,
    total_generated_chapters: 0,
    authoritative_completed: 0,
    library_indexed: 0,
    disk_chapters_with_final: 0,
    pending_total: 0,
    progress_note: '',
    pending_candidates_count: 0,
    avg_bounce_rate: 0,
    crisis_level: '正常',
  })
  const copyingTrial = ref(false)
  const virtualComments = ref<any[]>([])
  const loadingSerial = ref(false)
  const rewritingOutline = ref(false)
  const applyingOutline = ref(false)
  const outlineDiffDialogVisible = ref(false)
  const adaptiveOutlineDiff = ref({
    old_chapters: [] as any[],
    new_chapters: [] as any[],
  })
  const exportingSerial = ref(false)

  async function loadSerialData() {
    if (!currentProject.value?.id) return
    loadingSerial.value = true
    try {
      const pid = currentProject.value.id
      const [statusRes, commentsRes, candidatesRes, progressRes] = await Promise.all([
        getSerialStatus(pid),
        getProjectComments(pid),
        getProjectStateCandidates(pid),
        getNovelProgressSummary().catch(() => ({ data: {} })),
      ])
      serialStatus.value = statusRes.data
      const progress = progressRes.data || {}
      if (progress.authoritative_completed != null) {
        serialStatus.value.authoritative_completed = progress.authoritative_completed
      }
      if (progress.library_indexed != null) {
        serialStatus.value.library_indexed = progress.library_indexed
      }
      if (progress.progress_note) {
        serialStatus.value.progress_note = progress.progress_note
      }
      virtualComments.value = commentsRes.data
      const candidates = candidatesRes.data || []
      if (candidates.some((candidate: any) => candidate.status === 'pending')) {
        await approveAllProjectCandidates(pid)
      }
    } catch (error: any) {
      console.error('Failed to load serialization data', error)
    } finally {
      loadingSerial.value = false
    }
  }

  async function triggerAdaptiveRewrite() {
    if (!currentProject.value?.id) return
    rewritingOutline.value = true
    try {
      const pid = currentProject.value.id
      const { data } = await adaptiveRewriteOutline(pid)
      adaptiveOutlineDiff.value = {
        old_chapters: data.old_chapters || [],
        new_chapters: data.new_chapters || [],
      }
      if (adaptiveOutlineDiff.value.new_chapters.length === 0) {
        ElMessage.info('当前数据良好，无可调整章节。')
      } else {
        outlineDiffDialogVisible.value = true
      }
    } catch (error: any) {
      ElMessage.error(error?.response?.data?.detail || error.message || '大纲纠偏计算失败')
    } finally {
      rewritingOutline.value = false
    }
  }

  async function applyAdaptive() {
    if (!currentProject.value?.id) return
    applyingOutline.value = true
    try {
      const pid = currentProject.value.id
      await applyAdaptiveOutline(pid, { new_chapters: adaptiveOutlineDiff.value.new_chapters })
      ElMessage.success('智能纠偏大纲已成功应用到后续章节！')
      outlineDiffDialogVisible.value = false
      await loadSerialData()
    } catch (error: any) {
      ElMessage.error(error?.response?.data?.detail || error.message || '应用新大纲失败')
    } finally {
      applyingOutline.value = false
    }
  }

  async function copyTrialForPlatform() {
    copyingTrial.value = true
    try {
      const { data } = await exportChaptersTrial({ include_titles: true })
      await copyPlainTextToClipboard(data.text || '')
      ElMessage.success(`已复制 ${(data.chapter_ids || []).length} 章试发文本`)
    } catch (error: any) {
      ElMessage.error(error?.response?.data?.detail || error.message || '复制失败')
    } finally {
      copyingTrial.value = false
    }
  }

  async function downloadSerial(format: string) {
    if (!currentProject.value?.id) return
    exportingSerial.value = true
    try {
      const pid = currentProject.value.id
      const response = await exportSerial(pid, format)
      const blob = new Blob([response.data], {
        type: format === 'zip' ? 'application/zip' : 'text/plain;charset=utf-8',
      })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download =
        format === 'zip'
          ? `${currentProject.value.name}_已更新章节.zip`
          : `${currentProject.value.name}_连载全文.txt`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
      ElMessage.success('导出成功！')
    } catch (error: any) {
      ElMessage.error(
        error?.response?.data?.detail || error.message || '打包导出失败，可能暂无已生成章节',
      )
    } finally {
      exportingSerial.value = false
    }
  }

  return {
    serialStatus,
    copyingTrial,
    virtualComments,
    loadingSerial,
    rewritingOutline,
    applyingOutline,
    outlineDiffDialogVisible,
    adaptiveOutlineDiff,
    exportingSerial,
    loadSerialData,
    triggerAdaptiveRewrite,
    applyAdaptive,
    copyTrialForPlatform,
    downloadSerial,
  }
}