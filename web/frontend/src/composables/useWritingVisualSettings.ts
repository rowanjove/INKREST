import { nextTick, ref, watch, type Ref } from 'vue'

export type WriteTheme = 'white' | 'parchment' | 'green' | 'dark'

const STORAGE_KEYS = {
  theme: 'write_theme',
  fontSize: 'write_font_size',
  lineHeight: 'write_line_height',
  indent: 'write_indent',
  titleCenter: 'write_title_center',
} as const

export function useWritingVisualSettings(options: {
  editorRef: Ref<HTMLTextAreaElement | null>
  editorText: Ref<string>
}) {
  const { editorRef, editorText } = options

  const writeTheme = ref<WriteTheme>('white')
  const writeFontSize = ref(16)
  const writeLineHeight = ref(2.0)
  const writeIndent = ref(false)
  const writeTitleCenter = ref(false)

  function adjustTextareaHeight() {
    const textarea = editorRef.value
    if (!textarea) return
    textarea.style.height = 'auto'
    textarea.style.height = `${textarea.scrollHeight}px`
  }

  function loadVisualSettings() {
    try {
      writeTheme.value = (localStorage.getItem(STORAGE_KEYS.theme) as WriteTheme) || 'white'
      writeFontSize.value = Number.parseInt(localStorage.getItem(STORAGE_KEYS.fontSize) || '16', 10)
      writeLineHeight.value = Number.parseFloat(localStorage.getItem(STORAGE_KEYS.lineHeight) || '2.0')
      writeIndent.value = localStorage.getItem(STORAGE_KEYS.indent) === 'true'
      writeTitleCenter.value = localStorage.getItem(STORAGE_KEYS.titleCenter) === 'true'
    } catch {
      /* localStorage disabled */
    }
  }

  watch(editorText, () => {
    void nextTick(adjustTextareaHeight)
  })

  watch([writeTheme, writeFontSize, writeLineHeight, writeIndent, writeTitleCenter], () => {
    try {
      localStorage.setItem(STORAGE_KEYS.theme, writeTheme.value)
      localStorage.setItem(STORAGE_KEYS.fontSize, String(writeFontSize.value))
      localStorage.setItem(STORAGE_KEYS.lineHeight, String(writeLineHeight.value))
      localStorage.setItem(STORAGE_KEYS.indent, String(writeIndent.value))
      localStorage.setItem(STORAGE_KEYS.titleCenter, String(writeTitleCenter.value))
    } catch {
      /* localStorage error */
    }
  })

  return {
    writeTheme,
    writeFontSize,
    writeLineHeight,
    writeIndent,
    writeTitleCenter,
    adjustTextareaHeight,
    loadVisualSettings,
  }
}