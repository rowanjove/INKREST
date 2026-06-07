import { nextTick, ref, type Ref } from 'vue'
import { ElMessage } from 'element-plus'
import { apiErrorMessage, inlineExpand } from '../api'

export function useWritingEditorAssist(options: {
  editorRef: Ref<HTMLTextAreaElement | null>
  editorText: Ref<string>
  activeChapterId: Ref<string>
  currentChapter: Ref<any>
  handleSave: (silent?: boolean) => Promise<void>
}) {
  const { editorRef, editorText, activeChapterId, currentChapter, handleSave } = options

  const showBubble = ref(false)
  const bubbleX = ref(0)
  const bubbleY = ref(0)
  const selectedText = ref('')
  const expanding = ref(false)
  const expandResult = ref('')
  const showExpandDialog = ref(false)

  function resetAssistState() {
    showBubble.value = false
    expandResult.value = ''
    showExpandDialog.value = false
  }

  function handleKeyDown(event: KeyboardEvent) {
    if ((event.ctrlKey || event.metaKey) && event.key === 's') {
      event.preventDefault()
      void handleSave()
    }
  }

  function handleTextSelection(event: MouseEvent | KeyboardEvent) {
    if (!editorRef.value) return

    const selectionStart = editorRef.value.selectionStart
    const selectionEnd = editorRef.value.selectionEnd

    if (selectionStart !== selectionEnd) {
      const rawText = editorText.value.substring(selectionStart, selectionEnd)
      if (rawText.trim().length > 0) {
        selectedText.value = rawText
        const pointer = event as MouseEvent
        bubbleX.value = pointer.clientX || bubbleX.value || 300
        bubbleY.value = pointer.clientY || bubbleY.value || 200
        showBubble.value = true
        return
      }
    }
    showBubble.value = false
  }

  function handleAcceptRewrite(newText: string) {
    if (!editorRef.value) return
    const start = editorRef.value.selectionStart
    const end = editorRef.value.selectionEnd

    const originVal = editorText.value
    editorText.value = originVal.substring(0, start) + newText + originVal.substring(end)

    void nextTick(() => {
      if (editorRef.value) {
        editorRef.value.focus()
        editorRef.value.setSelectionRange(start, start + newText.length)
      }
    })

    ElMessage.success('已替换原段落！')
    showBubble.value = false
  }

  async function handleTriggerExpand() {
    if (!editorRef.value || expanding.value) return
    expanding.value = true
    expandResult.value = ''

    const cursorPosition = editorRef.value.selectionStart
    const beforeText = editorText.value.substring(0, cursorPosition)

    try {
      const { data } = await inlineExpand({
        before_text: beforeText,
        chapter_id: activeChapterId.value,
        goal: currentChapter.value?.plan?.chapter_goal || '',
      })
      expandResult.value = data.expanded_text
      showExpandDialog.value = true
    } catch (e: any) {
      ElMessage.error('续写失败: ' + apiErrorMessage(e, '续写失败'))
    } finally {
      expanding.value = false
    }
  }

  function handleAcceptExpand() {
    if (!editorRef.value || !expandResult.value) return
    const cursorPosition = editorRef.value.selectionStart
    const originVal = editorText.value

    editorText.value =
      originVal.substring(0, cursorPosition) + expandResult.value + originVal.substring(cursorPosition)

    showExpandDialog.value = false
    const insertedLen = expandResult.value.length
    expandResult.value = ''

    void nextTick(() => {
      if (editorRef.value) {
        editorRef.value.focus()
        editorRef.value.setSelectionRange(
          cursorPosition + insertedLen,
          cursorPosition + insertedLen,
        )
      }
    })
    ElMessage.success('续写内容已插入！')
  }

  return {
    showBubble,
    bubbleX,
    bubbleY,
    selectedText,
    expanding,
    expandResult,
    showExpandDialog,
    resetAssistState,
    handleKeyDown,
    handleTextSelection,
    handleAcceptRewrite,
    handleTriggerExpand,
    handleAcceptExpand,
  }
}