<script setup lang="ts">
import type { Editor as CoreEditor, JSONContent } from '@tiptap/core'
import { Editor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import {
  Back,
  Bottom,
  List,
  RefreshLeft,
  RefreshRight,
} from '@element-plus/icons-vue'
import { onBeforeUnmount, onMounted, shallowRef, watch } from 'vue'
import type { EditorSelection } from '../../entities/manuscript/manuscript'

const props = defineProps<{
  content: JSONContent
  preview: boolean
  fontSize: number
  lineHeight: number
}>()

const emit = defineEmits<{
  update: [content: JSONContent]
  selection: [selection: EditorSelection | null]
}>()

const editor = shallowRef<Editor>()
let applyingRemote = false

function currentSelection(instance: CoreEditor | undefined = editor.value): EditorSelection | null {
  if (!instance) return null
  const { from, to } = instance.state.selection
  if (from === to) return null
  const text = instance.state.doc.textBetween(from, to, '\n').trim()
  if (!text) return null
  const start = instance.view.coordsAtPos(from)
  const end = instance.view.coordsAtPos(to)
  return {
    text,
    from,
    to,
    x: Math.max(120, Math.min(window.innerWidth - 120, (start.left + end.right) / 2)),
    y: Math.max(64, start.top - 12),
  }
}

onMounted(() => {
  editor.value = new Editor({
    content: props.content,
    editable: !props.preview,
    extensions: [
      StarterKit,
      Placeholder.configure({ placeholder: '从这里开始写下这一章……' }),
    ],
    editorProps: {
      attributes: {
        class: 'manuscript-prose',
        spellcheck: 'true',
        'aria-label': '正文编辑器',
      },
    },
    onUpdate: ({ editor: instance }) => {
      if (!applyingRemote) emit('update', instance.getJSON())
    },
    onSelectionUpdate: ({ editor: instance }) => {
      emit('selection', currentSelection(instance))
    },
    onBlur: () => emit('selection', null),
  })
})

watch(
  () => props.content,
  (next) => {
    if (!editor.value) return
    const current = JSON.stringify(editor.value.getJSON())
    if (current === JSON.stringify(next)) return
    applyingRemote = true
    editor.value.commands.setContent(next, { emitUpdate: false })
    applyingRemote = false
  },
  { deep: true },
)

watch(
  () => props.preview,
  (preview) => editor.value?.setEditable(!preview),
)

onBeforeUnmount(() => editor.value?.destroy())

function replaceRange(from: number, to: number, replacement: string) {
  editor.value?.chain().focus().insertContentAt({ from, to }, replacement).run()
}

function insertAtCursor(replacement: string) {
  if (!editor.value) return
  const cursor = editor.value.state.selection.from
  editor.value.chain().focus().insertContentAt(cursor, replacement).run()
}

function getTextBeforeCursor() {
  if (!editor.value) return ''
  const cursor = editor.value.state.selection.from
  return editor.value.state.doc.textBetween(0, cursor, '\n')
}

function getCursorSelection(): EditorSelection {
  const cursor = editor.value?.state.selection.from ?? 1
  const coords = editor.value?.view.coordsAtPos(cursor)
  return {
    text: '',
    from: cursor,
    to: cursor,
    x: coords?.left ?? window.innerWidth / 2,
    y: coords?.top ?? 120,
  }
}

defineExpose({
  replaceRange,
  insertAtCursor,
  getTextBeforeCursor,
  getCursorSelection,
  focus: () => editor.value?.commands.focus(),
})
</script>

<template>
  <section
    class="editor-surface"
    :class="{ preview }"
    :style="{
      '--manuscript-font-size': `${fontSize}px`,
      '--manuscript-line-height': String(lineHeight),
    }"
  >
    <nav v-if="!preview" class="editor-toolbar" aria-label="正文格式">
      <el-button-group>
        <el-button
          :icon="RefreshLeft"
          aria-label="撤销"
          :disabled="!editor?.can().undo()"
          @click="editor?.chain().focus().undo().run()"
        />
        <el-button
          :icon="RefreshRight"
          aria-label="重做"
          :disabled="!editor?.can().redo()"
          @click="editor?.chain().focus().redo().run()"
        />
      </el-button-group>
      <span class="toolbar-divider" />
      <el-button
        :icon="Bottom"
        :type="editor?.isActive('heading', { level: 2 }) ? 'primary' : 'default'"
        @click="editor?.chain().focus().toggleHeading({ level: 2 }).run()"
      >
        小标题
      </el-button>
      <el-button
        :icon="List"
        :type="editor?.isActive('bulletList') ? 'primary' : 'default'"
        @click="editor?.chain().focus().toggleBulletList().run()"
      >
        列表
      </el-button>
      <el-button
        :icon="Back"
        :type="editor?.isActive('blockquote') ? 'primary' : 'default'"
        @click="editor?.chain().focus().toggleBlockquote().run()"
      >
        引用
      </el-button>
    </nav>
    <div class="paper">
      <EditorContent :editor="editor" />
    </div>
  </section>
</template>

<style scoped>
.editor-surface {
  height: 100%;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-canvas);
}
.editor-toolbar {
  min-height: 48px;
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 0 18px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-surface);
}
.toolbar-divider {
  width: 1px;
  height: 22px;
  margin: 0 3px;
  background: var(--color-border);
}
.paper {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: clamp(28px, 5vh, 64px) clamp(24px, 8vw, 110px) 35vh;
}
:deep(.tiptap) {
  width: min(100%, 780px);
  min-height: 64vh;
  margin: 0 auto;
  outline: none;
  color: var(--color-text-strong);
  font-family: "Noto Serif SC", "Songti SC", "SimSun", serif;
  font-size: var(--manuscript-font-size);
  line-height: var(--manuscript-line-height);
  letter-spacing: .025em;
}
:deep(.tiptap p) {
  margin: 0 0 .85em;
  text-indent: 2em;
}
:deep(.tiptap h2) {
  margin: 2em 0 1em;
  font-size: 1.25em;
  text-align: center;
}
:deep(.tiptap blockquote) {
  margin: 1.2em 0;
  padding: .2em 1em;
  border-left: 3px solid var(--color-primary);
  color: var(--color-text-muted);
}
:deep(.tiptap p.is-editor-empty:first-child::before) {
  content: attr(data-placeholder);
  float: left;
  height: 0;
  color: var(--color-text-subtle);
  pointer-events: none;
}
.preview .paper {
  background: var(--color-bg-surface);
}
.preview :deep(.tiptap) {
  max-width: 680px;
  font-size: calc(var(--manuscript-font-size) + 1px);
}
@media (max-width: 1100px) {
  .paper { padding-inline: 34px; }
  .editor-toolbar :deep(.el-button span) { display: none; }
}
</style>
