import { computed, nextTick, ref, type Ref } from 'vue'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import {
  apiErrorMessage,
  createChapter,
  deleteChapter,
  extractSyncAssets,
  getChapter,
  listChapters,
  listVersions,
  updateChapter,
  updateVersion,
} from '../api'
import { inferNextChapterId } from '../utils/dashboardEngine'

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

export function useWritingChapterEditor(options: {
  editorRef: Ref<HTMLTextAreaElement | null>
  adjustTextareaHeight: () => void
  assetSidebarRef: Ref<{ refreshAssets?: () => void } | null>
  rightTab: Ref<string>
  onChapterLoadStart?: () => void
  fetchScrapbook?: () => Promise<void>
}) {
  const { adjustTextareaHeight, assetSidebarRef, rightTab, onChapterLoadStart, fetchScrapbook } =
    options

  const chaptersList = ref<any[]>([])
  const activeChapterId = ref('')
  const currentChapter = ref<any>(null)
  const editorText = ref('')
  const loadingEditor = ref(false)
  const saving = ref(false)

  const versionsList = ref<any[]>([])
  const activeVersionId = ref('')
  const activeVersion = computed(() => versionsList.value.find((v) => v.id === activeVersionId.value))
  let loadSeq = 0

  async function fetchChapters() {
    try {
      const { data } = await listChapters({ offset: 0, limit: 500, sync: true })
      const chapterRows = data.items ?? data
      chaptersList.value = chapterRows || []

      if (chaptersList.value.length > 0 && !activeChapterId.value) {
        await loadChapter(chaptersList.value[0].chapter_id)
      }
    } catch (e: any) {
      ElMessage.error('获取章节列表失败: ' + apiErrorMessage(e, '获取章节列表失败'))
    }
  }

  async function loadChapter(cid: string) {
    const seq = ++loadSeq
    loadingEditor.value = true
    activeChapterId.value = cid
    onChapterLoadStart?.()

    try {
      const { data } = await getChapter(cid)
      if (seq !== loadSeq) return

      currentChapter.value = data

      const { data: vData } = await listVersions(cid)
      if (seq !== loadSeq) return
      versionsList.value = vData || []

      const activeV = versionsList.value.find((v: any) => v.is_active === 1)
      if (activeV) {
        activeVersionId.value = activeV.id
        editorText.value = activeV.content || ''
      } else if (versionsList.value.length > 0) {
        activeVersionId.value = versionsList.value[0].id
        editorText.value = versionsList.value[0].content || ''
      } else {
        activeVersionId.value = ''
        editorText.value = data.final_text || ''
      }

      if (rightTab.value === 'scrapbook' && fetchScrapbook) {
        await fetchScrapbook()
        if (seq !== loadSeq) return
      }

      void nextTick(adjustTextareaHeight)
    } catch (e: any) {
      if (seq !== loadSeq) return
      ElMessage.error('加载章节内容失败: ' + apiErrorMessage(e, '加载章节内容失败'))
      editorText.value = ''
      currentChapter.value = null
    } finally {
      if (seq === loadSeq) {
        loadingEditor.value = false
      }
    }
  }

  async function handleSave(silent = false) {
    if (!activeChapterId.value || saving.value || loadingEditor.value) return
    saving.value = true

    try {
      const curVer = activeVersion.value
      if (curVer && curVer.is_active === 0) {
        await updateVersion(activeVersionId.value, {
          content: editorText.value,
        })
        if (!silent) {
          ElMessage.success('分支剧情草稿已保存！')
        }
      } else {
        await updateChapter(activeChapterId.value, {
          title: currentChapter.value?.title || '',
          final_text: editorText.value,
        })
        if (!silent) {
          ElMessage.success('章节内容已保存！')
        }
      }

      await fetchChapters()
      const { data: vData } = await listVersions(activeChapterId.value)
      versionsList.value = vData || []

      if (!silent) {
        const { data } = await extractSyncAssets({ chapter_text: editorText.value })
        if (data.success && data.synced && data.synced.length > 0) {
          const created = data.synced
            .filter((s: any) => s.status === 'created')
            .map((s: any) => s.label)
          const updated = data.synced
            .filter((s: any) => s.status === 'updated')
            .map((s: any) => s.label)

          let message = ''
          if (created.length) {
            message += `✨ <strong>新增设定</strong>: ${created.map(escapeHtml).join('，')}<br />`
          }
          if (updated.length) {
            message += `🔄 <strong>更新设定</strong>: ${updated.map(escapeHtml).join('，')}<br />`
          }

          ElNotification({
            title: '资产库自动同步成功',
            message,
            type: 'success',
            duration: 5000,
            dangerouslyUseHTMLString: true,
          })

          assetSidebarRef.value?.refreshAssets?.()
        }
      }
    } catch (e: any) {
      if (!silent) {
        ElMessage.error('保存失败: ' + apiErrorMessage(e, '保存失败'))
      }
    } finally {
      saving.value = false
    }
  }

  function handleOpenCreateChapter() {
    const nextIdStr = inferNextChapterId(chaptersList.value)

    ElMessageBox.prompt('请输入新建章节的标题', '新建章节', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputValue: `第 ${Number.parseInt(nextIdStr, 10)} 章`,
      inputPattern: /.+/,
      inputErrorMessage: '标题不能为空',
    })
      .then(async ({ value }) => {
        try {
          await createChapter({
            chapter_id: nextIdStr,
            title: value.trim(),
          })
          ElMessage.success('章节创建成功！')
          await fetchChapters()
          await loadChapter(nextIdStr)
        } catch (e: any) {
          ElMessage.error('创建章节失败: ' + apiErrorMessage(e, '创建章节失败'))
        }
      })
      .catch(() => {})
  }

  async function handleDeleteChapter(chapterId: string) {
    try {
      await ElMessageBox.confirm(
        `确定删除章节 ${chapterId}？正文、计划、报告、历史版本，以及状态库中该章同步的事件/人物/伏笔等数据都会一并移除。`,
        '删除章节',
        {
          confirmButtonText: '删除',
          cancelButtonText: '取消',
          type: 'warning',
        },
      )
      await deleteChapter(chapterId)
      if (activeChapterId.value === chapterId) {
        activeChapterId.value = ''
        currentChapter.value = null
        editorText.value = ''
        versionsList.value = []
        activeVersionId.value = ''
      }
      await fetchChapters()
      ElMessage.success(`章节 ${chapterId} 已删除`)
    } catch (error: any) {
      if (error !== 'cancel' && error !== 'close') {
        ElMessage.error('删除章节失败: ' + apiErrorMessage(error, '删除章节失败'))
      }
    }
  }

  async function openChapterFromQuery(raw: unknown) {
    if (typeof raw !== 'string' || !raw.trim()) return
    const cid = raw.trim()
    if (chaptersList.value.some((ch) => ch.chapter_id === cid)) {
      await loadChapter(cid)
    }
  }

  async function handleForceRefresh() {
    if (!activeChapterId.value) return
    try {
      await loadChapter(activeChapterId.value)
      ElMessage.success('当前章节内容已重新载入！')
    } catch (error: any) {
      ElMessage.error('刷新失败：' + error.message)
    }
  }

  return {
    chaptersList,
    activeChapterId,
    currentChapter,
    editorText,
    loadingEditor,
    saving,
    versionsList,
    activeVersionId,
    activeVersion,
    fetchChapters,
    loadChapter,
    handleSave,
    handleOpenCreateChapter,
    handleDeleteChapter,
    openChapterFromQuery,
    handleForceRefresh,
  }
}