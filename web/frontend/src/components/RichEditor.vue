<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue'

const props = defineProps<{
  modelValue: string
  placeholder?: string
  minHeight?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  save: [value: string]
}>()

const editorRef = ref<HTMLTextAreaElement | null>(null)
const localValue = ref(props.modelValue)
let saveTimer: number | undefined

watch(() => props.modelValue, (val) => {
  localValue.value = val
})

const onInput = (e: Event) => {
  const target = e.target as HTMLTextAreaElement
  localValue.value = target.value
  emit('update:modelValue', target.value)

  // Auto-save after 2 seconds of inactivity
  if (saveTimer) window.clearTimeout(saveTimer)
  saveTimer = window.setTimeout(() => {
    emit('save', target.value)
  }, 2000)
}

const handleKeydown = (e: KeyboardEvent) => {
  // Ctrl+S / Cmd+S to save
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault()
    emit('save', localValue.value)
  }

  // Tab for indentation
  if (e.key === 'Tab') {
    e.preventDefault()
    const textarea = editorRef.value
    if (!textarea) return
    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const value = textarea.value
    localValue.value = value.substring(0, start) + '  ' + value.substring(end)
    emit('update:modelValue', localValue.value)
    requestAnimationFrame(() => {
      textarea.selectionStart = textarea.selectionEnd = start + 2
    })
  }
}

onUnmounted(() => {
  if (saveTimer) window.clearTimeout(saveTimer)
})
</script>

<template>
  <div class="rich-editor">
    <div class="editor-toolbar">
      <slot name="toolbar" />
      <span class="save-hint">Ctrl+S 保存 | Tab 缩进</span>
    </div>
    <textarea
      ref="editorRef"
      :value="localValue"
      @input="onInput"
      @keydown="handleKeydown"
      :placeholder="placeholder || '开始写作...'"
      class="editor-textarea"
      :style="{ minHeight: minHeight || '400px' }"
      spellcheck="false"
    />
  </div>
</template>

<style scoped>
.rich-editor {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--border-light);
  border-radius: 12px;
  overflow: hidden;
  background: var(--color-bg-surface);
}
.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: #fafafa;
  border-bottom: 1px solid var(--border-light);
  min-height: 40px;
}
.save-hint {
  font-size: 11px;
  color: var(--text-muted);
}
.editor-textarea {
  width: 100%;
  padding: 20px 24px;
  border: none;
  outline: none;
  resize: vertical;
  font-family: var(--font-serif);
  font-size: 16px;
  line-height: 2;
  color: #2b2b2b;
  background: #fefdfb;
}
.editor-textarea::placeholder {
  color: #c0c4cc;
}
.editor-textarea:focus {
  background: var(--color-bg-surface);
}
</style>
