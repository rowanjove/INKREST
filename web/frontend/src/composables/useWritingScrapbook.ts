import { nextTick, ref, watch, type Ref } from 'vue'
import { ElMessage } from 'element-plus'
import { apiErrorMessage, getScrapbook } from '../api'

export function useWritingScrapbook(options: {
  activeChapterId: Ref<string>
  editorText: Ref<string>
  editorRef: Ref<HTMLTextAreaElement | null>
  adjustTextareaHeight: () => void
  rightTab: Ref<'assets' | 'scrapbook' | 'feedback' | 'golden'>
}) {
  const { activeChapterId, editorText, editorRef, adjustTextareaHeight, rightTab } = options

  const scrapbookList = ref<any[]>([])
  const scrapbookQuery = ref('')
  const loadingScrapbook = ref(false)

  async function fetchScrapbook() {
    loadingScrapbook.value = true
    try {
      const { data } = await getScrapbook({
        query: scrapbookQuery.value,
        chapter_id: activeChapterId.value,
      })
      scrapbookList.value = data || []
    } catch (e: any) {
      ElMessage.error('获取废稿段落失败: ' + apiErrorMessage(e, '获取废稿段落失败'))
    } finally {
      loadingScrapbook.value = false
    }
  }

  function copyScrapbookText(text: string) {
    navigator.clipboard.writeText(text)
    ElMessage.success('已复制废稿段落到剪贴板')
  }

  function insertScrapbookText(text: string) {
    if (!editorRef.value) return
    const start = editorRef.value.selectionStart
    const originVal = editorText.value
    editorText.value = originVal.substring(0, start) + text + originVal.substring(start)
    void nextTick(() => {
      if (editorRef.value) {
        editorRef.value.focus()
        editorRef.value.setSelectionRange(start + text.length, start + text.length)
        adjustTextareaHeight()
      }
    })
    ElMessage.success('废稿段落已成功插入编辑器！')
  }

  watch(rightTab, (val) => {
    if (val === 'scrapbook') {
      void fetchScrapbook()
    }
  })

  return {
    scrapbookList,
    scrapbookQuery,
    loadingScrapbook,
    fetchScrapbook,
    copyScrapbookText,
    insertScrapbookText,
  }
}