import { nextTick, ref, type Ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  apiErrorMessage,
  createSnapshot,
  getTask,
  runChapter,
  suggestChapterGoal,
} from '../api'

export function useWritingAiWrite(options: {
  activeChapterId: Ref<string>
  editorText: Ref<string>
  loadingEditor: Ref<boolean>
  loadChapter: (cid: string) => Promise<void>
  fetchChapters: () => Promise<void>
  adjustTextareaHeight: () => void
  writeTitleCenter: Ref<boolean>
  writeIndent: Ref<boolean>
}) {
  const {
    activeChapterId,
    editorText,
    loadingEditor,
    loadChapter,
    fetchChapters,
    adjustTextareaHeight,
    writeTitleCenter,
    writeIndent,
  } = options

  const writing = ref(false)
  const writeDialogOpen = ref(false)
  const chapterGoalForWrite = ref('')
  let aiWritePollTimer: number | null = null

  function stopAiWritePolling() {
    if (aiWritePollTimer) {
      window.clearInterval(aiWritePollTimer)
      aiWritePollTimer = null
    }
  }

  function pollAiWriteResult(taskId: string, chapterId: string) {
    stopAiWritePolling()
    aiWritePollTimer = window.setInterval(async () => {
      try {
        const { data } = await getTask(taskId)
        if (data.status === 'completed') {
          stopAiWritePolling()
          await loadChapter(chapterId)
          await fetchChapters()
          ElMessage.success('AI 写作已完成，正文已自动载入写作页。')
        } else if (data.status === 'failed') {
          stopAiWritePolling()
          ElMessage.error(data.error || 'AI 写作任务失败')
        }
      } catch {
        stopAiWritePolling()
      }
    }, 2000)
  }

  async function handleTriggerWrite() {
    if (!activeChapterId.value) return

    if (editorText.value.trim().length > 0) {
      try {
        await ElMessageBox.confirm(
          '该章节目前已有正文内容。触发 [AI 写作] 将重新生成整章并覆盖当前编辑内容（覆盖前系统会自动备份快照）。是否继续？',
          'AI 写作警告',
          {
            confirmButtonText: '继续',
            cancelButtonText: '取消',
            type: 'warning',
          },
        )
        await createSnapshot(activeChapterId.value, { title: 'AI写作前自动备份（原正文）' })
      } catch {
        return
      }
    }

    loadingEditor.value = true
    try {
      const { data } = await suggestChapterGoal(activeChapterId.value)
      chapterGoalForWrite.value = data.goal || ''
      writeDialogOpen.value = true
    } catch (e: any) {
      ElMessage.error('获取章节大纲目标失败: ' + apiErrorMessage(e, '获取章节大纲目标失败'))
    } finally {
      loadingEditor.value = false
    }
  }

  async function handleStartAiWrite() {
    if (!chapterGoalForWrite.value.trim()) {
      ElMessage.warning('章节写作目标不能为空')
      return
    }
    writing.value = true
    try {
      const { data } = await runChapter({
        chapter_id: activeChapterId.value,
        goal: chapterGoalForWrite.value,
        dry_run: false,
      })
      pollAiWriteResult(data.id, activeChapterId.value)
      ElMessage.success('AI 写作任务已提交，完成后正文会自动载入当前写作页。')
      writeDialogOpen.value = false
    } catch (e: any) {
      ElMessage.error('启动 AI 写作失败: ' + apiErrorMessage(e, '启动 AI 写作失败'))
    } finally {
      writing.value = false
    }
  }

  function handleAutoFormat() {
    writeTitleCenter.value = true
    writeIndent.value = true

    if (editorText.value) {
      const lines = editorText.value.split('\n')
      const formattedLines = lines.map((line) => {
        let trimmed = line.trim()
        trimmed = trimmed.replace(/^[ 　]+/g, '')
        return trimmed
      })

      let resultText = formattedLines.join('\n')
      resultText = resultText.replace(/\n{3,}/g, '\n\n')

      editorText.value = resultText
      void nextTick(adjustTextareaHeight)
    }
    ElMessage.success('一键排版完成！已自动将标题居中并启用首行缩进。')
  }

  return {
    writing,
    writeDialogOpen,
    chapterGoalForWrite,
    stopAiWritePolling,
    pollAiWriteResult,
    handleTriggerWrite,
    handleStartAiWrite,
    handleAutoFormat,
  }
}