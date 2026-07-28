<script setup lang="ts">
import { computed, ref, watch } from 'vue'

const props = defineProps<{
  modelValue: string
  title: string
  path: string
  showSource?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'save': []
}>()

const localContent = ref(props.modelValue)

watch(() => props.modelValue, (newVal) => {
  localContent.value = newVal
})

const onInput = (val: string) => {
  localContent.value = val
  emit('update:modelValue', val)
}

const handleKeydown = (e: KeyboardEvent) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault()
    emit('save')
  }
}

// Simple but elegant markdown to HTML compiler for preview
const renderedHtml = computed(() => {
  const raw = localContent.value || ''
  
  // Escape HTML tags to prevent XSS in preview
  let html = raw
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  // Compile headers
  html = html.replace(/^### (.*?)$/gm, '<h3>$1</h3>')
  html = html.replace(/^## (.*?)$/gm, '<h2>$1</h2>')
  html = html.replace(/^# (.*?)$/gm, '<h1>$1</h1>')

  // Horizontal Rule
  html = html.replace(/^---$/gm, '<hr class="preview-hr" />')

  // Bold & Italic
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>')

  // Process lists and paragraphs line-by-line
  const lines = html.split('\n')
  let inList = false
  const processed = []

  for (let line of lines) {
    const trimmed = line.trim()
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      const content = trimmed.substring(2)
      if (!inList) {
        processed.push('<ul class="preview-list">')
        inList = true
      }
      processed.push(`<li>${content}</li>`)
    } else {
      if (inList) {
        processed.push('</ul>')
        inList = false
      }
      if (trimmed === '') {
        processed.push('<div class="preview-spacer"></div>')
      } else if (!trimmed.startsWith('<h') && !trimmed.startsWith('<hr')) {
        processed.push(`<p class="preview-p">${line}</p>`)
      } else {
        processed.push(line)
      }
    }
  }

  if (inList) {
    processed.push('</ul>')
  }

  return processed.join('\n')
})
</script>

<template>
  <div class="markdown-workspace" :class="{ 'preview-only': !showSource }">
    <div v-if="showSource" class="workspace-editor">
      <div class="pane-header">
        <span>编辑源码</span>
        <span class="hint">支持 Ctrl+S 保存</span>
      </div>
      <el-input
        v-model="localContent"
        type="textarea"
        resize="none"
        class="editor-textarea"
        spellcheck="false"
        placeholder="# 在此输入 Markdown 设定..."
        @input="onInput"
        @keydown="handleKeydown"
      />
    </div>

    <div class="workspace-preview">
      <div class="pane-header">
        <span>实时预览</span>
        <span class="badge">已渲染</span>
      </div>
      <div class="preview-body" v-html="renderedHtml"></div>
    </div>
  </div>
</template>

<style scoped>
.markdown-workspace {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1px;
  background: #e5e7eb;
  height: 100%;
  min-height: 500px;
  overflow: hidden;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.markdown-workspace.preview-only {
  grid-template-columns: minmax(0, 1fr);
}

.workspace-editor,
.workspace-preview {
  background: var(--color-bg-surface);
  display: flex;
  flex-direction: column;
  height: 100%;
}

.pane-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: #f9fafb;
  border-bottom: 1px solid var(--color-border-subtle);
  font-size: 13px;
  font-weight: 600;
  color: #4b5563;
}

.hint {
  font-size: 11px;
  color: #9ca3af;
  font-weight: normal;
}

.badge {
  font-size: 11px;
  background: #ecfdf5;
  color: var(--color-success);
  padding: 2px 6px;
  border-radius: 999px;
  font-weight: 600;
}

.editor-textarea {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.editor-textarea :deep(.el-textarea__inner) {
  flex: 1;
  height: 100%;
  border: 0;
  border-radius: 0;
  box-shadow: none;
  padding: 18px 24px;
  font-family: "Cascadia Mono", Consolas, Monaco, monospace;
  font-size: 14px;
  line-height: 1.7;
  color: #1f2937;
  resize: none;
}

.preview-body {
  flex: 1;
  padding: 24px 32px;
  overflow-y: auto;
  background: #fbfbf9; /* Soft paper color for reading */
  color: #2c3e50;
  font-family: "Georgia", "Times New Roman", "PingFang SC", "Microsoft YaHei", serif;
  font-size: 16px;
  line-height: 1.85;
}

/* Rendered markdown styles */
.preview-body :deep(h1) {
  font-size: 26px;
  font-weight: 800;
  color: #111827;
  margin-top: 0;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 2px solid #e5e7eb;
}

.preview-body :deep(h2) {
  font-size: 20px;
  font-weight: 700;
  color: #1f2937;
  margin-top: 24px;
  margin-bottom: 12px;
  padding-bottom: 6px;
  border-bottom: 1px solid #f3f4f6;
}

.preview-body :deep(h3) {
  font-size: 17px;
  font-weight: 700;
  color: #374151;
  margin-top: 18px;
  margin-bottom: 8px;
}

.preview-body :deep(.preview-p) {
  margin: 0 0 14px;
  text-align: justify;
}

.preview-body :deep(.preview-list) {
  margin: 0 0 16px;
  padding-left: 20px;
  list-style-type: disc;
}

.preview-body :deep(.preview-list li) {
  margin-bottom: 6px;
}

.preview-body :deep(.preview-hr) {
  border: 0;
  border-top: 1px solid #e5e7eb;
  margin: 20px 0;
}

.preview-body :deep(.preview-spacer) {
  height: 12px;
}

.preview-body :deep(strong) {
  color: #111827;
  font-weight: 700;
}

.preview-body :deep(em) {
  font-style: italic;
}
</style>
