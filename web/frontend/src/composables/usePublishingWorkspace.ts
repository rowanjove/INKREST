import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import type { LocationQueryRaw } from 'vue-router'

import {
  exportPublication,
  getPublishingWorkspace,
  savePublishingFeedback,
  updatePublishingPlatform,
} from '../api/publishing'
import type {
  ExportFormat,
  PublishingTab,
  PublishingWorkspace,
  ReaderSettings,
} from '../entities/publishing/publishing'

const TABS = new Set<PublishingTab>(['preview', 'platform', 'export'])
const SETTINGS_KEY = 'inkrest-publication-reader'

function routeTab(value: unknown): PublishingTab {
  return typeof value === 'string' && TABS.has(value as PublishingTab)
    ? (value as PublishingTab)
    : 'preview'
}

function loadReaderSettings(): ReaderSettings {
  const fallback: ReaderSettings = {
    fontSize: 18,
    lineHeight: 1.9,
    width: 760,
    indent: true,
  }
  try {
    const stored = JSON.parse(localStorage.getItem(SETTINGS_KEY) || '{}')
    return { ...fallback, ...stored }
  } catch {
    localStorage.removeItem(SETTINGS_KEY)
    return fallback
  }
}

function saveBlob(blob: Blob, filename: string) {
  const href = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = href
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  window.setTimeout(() => URL.revokeObjectURL(href), 0)
}

export function usePublishingWorkspace() {
  const route = useRoute()
  const router = useRouter()
  const workspace = ref<PublishingWorkspace | null>(null)
  const loading = ref(false)
  const chapterLoading = ref(false)
  const saving = ref(false)
  const exporting = ref(false)
  const error = ref('')
  const activeTab = ref<PublishingTab>(routeTab(route.query.tab))
  const selectedChapterId = ref(
    typeof route.query.chapter === 'string' ? route.query.chapter : '',
  )
  const catalogQuery = ref('')
  const readerSettings = ref<ReaderSettings>(loadReaderSettings())
  const exportFormat = ref<ExportFormat>('txt')
  const exportScope = ref<'all' | 'chapter'>('all')
  const exportTitle = ref('')
  let loadSequence = 0

  const filteredChapters = computed(() => {
    const chapters = workspace.value?.chapters.filter((chapter) => chapter.has_content) || []
    const needle = catalogQuery.value.trim().toLocaleLowerCase()
    if (!needle) return chapters
    return chapters.filter((chapter) =>
      `${chapter.chapter_id} ${chapter.title}`.toLocaleLowerCase().includes(needle),
    )
  })
  const paragraphs = computed(() =>
    (workspace.value?.selected_chapter?.plain_text || '')
      .split(/\n+/u)
      .map((line) => line.trim())
      .filter(Boolean),
  )
  const readerStyle = computed(() => ({
    maxWidth: `${readerSettings.value.width}px`,
    fontSize: `${readerSettings.value.fontSize}px`,
    lineHeight: String(readerSettings.value.lineHeight),
  }))
  const selectedIndex = computed(() =>
    (workspace.value?.chapters.filter((chapter) => chapter.has_content) || []).findIndex(
      (chapter) => chapter.chapter_id === selectedChapterId.value,
    ),
  )
  const currentFeedback = computed(() =>
    workspace.value?.feedback.find(
      (item) => item.chapter_id === selectedChapterId.value,
    ),
  )

  async function load(chapterId = selectedChapterId.value, options: { quiet?: boolean } = {}) {
    const sequence = ++loadSequence
    if (workspace.value && chapterId) chapterLoading.value = true
    else if (!options.quiet) loading.value = true
    error.value = ''
    try {
      const { data } = await getPublishingWorkspace(chapterId)
      if (sequence !== loadSequence) return
      workspace.value = data
      selectedChapterId.value = data.selected_chapter_id
      if (!exportTitle.value) exportTitle.value = data.book.title
    } catch (reason: any) {
      if (sequence !== loadSequence) return
      error.value =
        reason?.response?.data?.detail || reason?.message || '发布中心加载失败'
    } finally {
      if (sequence === loadSequence) {
        loading.value = false
        chapterLoading.value = false
      }
    }
  }

  function syncQuery() {
    const query: LocationQueryRaw = { ...route.query, tab: activeTab.value }
    if (selectedChapterId.value) query.chapter = selectedChapterId.value
    else delete query.chapter
    void router.replace({ path: '/publishing', query })
  }

  async function selectChapter(chapterId: string) {
    if (!chapterId || chapterId === selectedChapterId.value) return
    selectedChapterId.value = chapterId
    await load(chapterId, { quiet: true })
    requestAnimationFrame(() => {
      document.querySelector('.publication-reader-scroll')?.scrollTo({
        top: 0,
        behavior: 'smooth',
      })
    })
  }

  async function savePlatform(platform: string) {
    if (!workspace.value || saving.value || platform === workspace.value.platform.id) return
    saving.value = true
    try {
      const { data } = await updatePublishingPlatform(platform)
      workspace.value = data
      ElMessage.success('目标平台已更新')
    } catch (reason: any) {
      ElMessage.error(reason?.response?.data?.detail || reason?.message || '平台保存失败')
    } finally {
      saving.value = false
    }
  }

  async function saveFeedback(data: {
    bounce_rate: number
    retention_rate: number
    active_readers: number
  }) {
    if (!selectedChapterId.value || saving.value) return
    saving.value = true
    try {
      const response = await savePublishingFeedback({
        chapter_id: selectedChapterId.value,
        ...data,
      })
      workspace.value = response.data
      ElMessage.success('外站读者反馈已保存')
    } catch (reason: any) {
      ElMessage.error(reason?.response?.data?.detail || reason?.message || '反馈保存失败')
    } finally {
      saving.value = false
    }
  }

  async function download() {
    const value = workspace.value
    if (!value || exporting.value) return
    if (!value.preflight.can_export) {
      ElMessage.error('请先处理发布预检中的阻断项')
      return
    }
    const format = value.formats.find((item) => item.id === exportFormat.value)
    if (!format?.available) {
      ElMessage.warning(`${format?.label || exportFormat.value} 导出组件尚未安装`)
      return
    }
    const warnings = value.preflight.items
      .filter((item) => item.severity === 'warning')
      .map((item) => item.label)
    const scopeLabel =
      exportScope.value === 'chapter'
        ? `仅第 ${selectedChapterId.value} 章`
        : `全书 ${value.book.chapter_count} 章`
    try {
      await ElMessageBox.confirm(
        [
          `${scopeLabel}将导出为 ${format.label}。`,
          warnings.length ? `仍有提示：${warnings.join('；')}。` : '发布预检已通过。',
          '文件内容以当前已保存的数据库文稿为准。',
        ].join('\n'),
        '确认导出',
        {
          confirmButtonText: '确认下载',
          cancelButtonText: '返回检查',
          type: warnings.length ? 'warning' : 'success',
          distinguishCancelAndClose: true,
        },
      )
    } catch {
      return
    }
    exporting.value = true
    try {
      const { data } = await exportPublication({
        format: exportFormat.value,
        title: exportTitle.value.trim() || value.book.title,
        chapter_ids:
          exportScope.value === 'chapter' && selectedChapterId.value
            ? [selectedChapterId.value]
            : [],
        acknowledge_warnings: true,
      })
      saveBlob(
        data,
        `${exportTitle.value.trim() || value.book.title}${format.extension}`,
      )
      ElMessage.success(`${format.label} 已生成`)
    } catch (reason: any) {
      ElMessage.error(reason?.message || '导出失败，请查看诊断日志')
    } finally {
      exporting.value = false
    }
  }

  watch([activeTab, selectedChapterId], syncQuery)
  watch(
    () => route.query.tab,
    (value) => {
      activeTab.value = routeTab(value)
    },
  )
  watch(
    readerSettings,
    (value) => localStorage.setItem(SETTINGS_KEY, JSON.stringify(value)),
    { deep: true },
  )

  onMounted(() => void load())

  return {
    workspace,
    loading,
    chapterLoading,
    saving,
    exporting,
    error,
    activeTab,
    selectedChapterId,
    selectedIndex,
    catalogQuery,
    readerSettings,
    readerStyle,
    filteredChapters,
    paragraphs,
    currentFeedback,
    exportFormat,
    exportScope,
    exportTitle,
    load,
    selectChapter,
    savePlatform,
    saveFeedback,
    download,
  }
}
