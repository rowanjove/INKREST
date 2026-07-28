<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Pane, Splitpanes } from 'splitpanes'
import 'splitpanes/dist/splitpanes.css'
import {
  ArrowLeft,
  ArrowRight,
  FullScreen,
  MagicStick,
} from '@element-plus/icons-vue'
import type { SplitpanesResizedPayload } from 'splitpanes'
import { ElMessage } from 'element-plus'
import { inlineExpand, inlineRewrite } from '../api'
import ManuscriptChapterTree from '../components/manuscript/ManuscriptChapterTree.vue'
import ManuscriptEditor from '../components/manuscript/ManuscriptEditor.vue'
import ManuscriptInspector from '../components/manuscript/ManuscriptInspector.vue'
import { useManuscriptWorkspace } from '../composables/useManuscriptWorkspace'
import type {
  AiEditIntent,
  AiEditKind,
  AiEditSuggestion,
  EditorSelection,
  ManuscriptRevision,
} from '../entities/manuscript/manuscript'
import {
  SAVE_STATUS_LABELS,
  createAiEditIntent,
  saveStatusTone,
} from '../entities/manuscript/manuscript'
import ErrorState from '../shared/ui/ErrorState.vue'
import StatusBadge from '../shared/ui/StatusBadge.vue'

type EditorHandle = {
  replaceRange: (from: number, to: number, replacement: string) => void
  insertAtCursor: (replacement: string) => void
  getTextBeforeCursor: () => string
  getCursorSelection: () => EditorSelection
  focus: () => void
}

type InspectorHandle = { showAiTab: () => void }

const route = useRoute()
const router = useRouter()
const editorRef = ref<EditorHandle | null>(null)
const inspectorDesktopRef = ref<InspectorHandle | null>(null)
const inspectorMobileRef = ref<InspectorHandle | null>(null)
const selection = ref<EditorSelection | null>(null)
const aiIntent = ref<AiEditIntent | null>(null)
const aiSuggestion = ref<AiEditSuggestion | null>(null)
const aiLoading = ref(false)
const preview = ref(false)
const focusMode = ref(localStorage.getItem('manuscript-focus-mode') === '1')
const leftVisible = ref(localStorage.getItem('manuscript-left-visible') !== '0')
const rightVisible = ref(localStorage.getItem('manuscript-right-visible') !== '0')
const fontSize = ref(Number(localStorage.getItem('manuscript-font-size') || 18))
const lineHeight = ref(Number(localStorage.getItem('manuscript-line-height') || 2))
const leftSize = ref(Number(localStorage.getItem('manuscript-left-size') || 19))
const rightSize = ref(Number(localStorage.getItem('manuscript-right-size') || 19))
const mobile = ref(false)
const mobileLeftOpen = ref(false)
const mobileRightOpen = ref(false)
const revisionPreview = ref<ManuscriptRevision | null>(null)
const nextUpdateSource = ref<'autosave' | 'ai_accept'>('autosave')

const {
  workspace,
  document,
  content,
  title,
  loading,
  loadError,
  saveStatus,
  saveError,
  conflictDocument,
  activeChapterId,
  load,
  selectChapter,
  updateContent,
  updateTitle,
  saveNow,
  useServerVersion,
  keepLocalAsNewRevision,
  restoreRevision,
} = useManuscriptWorkspace()

const centerSize = computed(() => {
  const left = leftVisible.value && !focusMode.value ? leftSize.value : 0
  const right = rightVisible.value && !focusMode.value ? rightSize.value : 0
  return Math.max(60, 100 - left - right)
})
const showSelectionMenu = computed(
  () => Boolean(selection.value && !preview.value && !aiIntent.value && !aiSuggestion.value),
)

let mediaQuery: MediaQueryList | null = null
const updateMobile = () => {
  mobile.value = Boolean(mediaQuery?.matches)
}

async function openChapter(chapterId: string) {
  if (!(await selectChapter(chapterId))) return
  selection.value = null
  aiIntent.value = null
  aiSuggestion.value = null
  mobileLeftOpen.value = false
  await router.replace({ path: '/writer', query: { chapter: chapterId } })
}

function openAiIntent(kind: AiEditKind) {
  const currentSelection =
    kind === 'continue' ? editorRef.value?.getCursorSelection() : selection.value
  if (!currentSelection || !activeChapterId.value) return
  aiIntent.value = createAiEditIntent(kind, activeChapterId.value, currentSelection)
  aiSuggestion.value = null
  selection.value = null
  rightVisible.value = true
  mobileRightOpen.value = mobile.value
  void nextTick(() => {
    inspectorDesktopRef.value?.showAiTab()
    inspectorMobileRef.value?.showAiTab()
  })
}

async function confirmAiIntent() {
  if (!aiIntent.value || aiLoading.value) return
  aiLoading.value = true
  try {
    let replacement = ''
    if (aiIntent.value.kind === 'continue') {
      const { data } = await inlineExpand({
        before_text: editorRef.value?.getTextBeforeCursor() || '',
        chapter_id: aiIntent.value.chapterId,
        goal: workspace.value.context.chapter_goal || '',
      })
      replacement = data.expanded_text
    } else {
      const { data } = await inlineRewrite({
        text: aiIntent.value.selection.text,
        instruction: aiIntent.value.instruction,
        chapter_id: aiIntent.value.chapterId,
        goal: workspace.value.context.chapter_goal || '',
      })
      replacement = data.rewritten_text
    }
    aiSuggestion.value = { ...aiIntent.value, replacement }
    aiIntent.value = null
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : 'AI 建议生成失败')
  } finally {
    aiLoading.value = false
  }
}

function cancelAi() {
  aiIntent.value = null
  aiSuggestion.value = null
  editorRef.value?.focus()
}

function acceptAi() {
  const suggestion = aiSuggestion.value
  if (!suggestion) return
  nextUpdateSource.value = 'ai_accept'
  if (suggestion.kind === 'continue') {
    editorRef.value?.insertAtCursor(suggestion.replacement)
  } else {
    editorRef.value?.replaceRange(
      suggestion.selection.from,
      suggestion.selection.to,
      suggestion.replacement,
    )
  }
  aiSuggestion.value = null
  ElMessage.success('建议已采纳，正在自动保存')
}

function handleEditorUpdate(next: Parameters<typeof updateContent>[0]) {
  updateContent(next, nextUpdateSource.value)
  nextUpdateSource.value = 'autosave'
}

async function restorePreviewedRevision() {
  if (!revisionPreview.value) return
  const succeeded = await restoreRevision(revisionPreview.value)
  if (succeeded) {
    revisionPreview.value = null
    ElMessage.success('已恢复为新的当前修订')
  }
}

function updatePaneSizes(payload: SplitpanesResizedPayload) {
  const panes = payload.panes
  if (panes.length !== 3) return
  leftSize.value = Math.round(panes[0]!.size * 10) / 10
  rightSize.value = Math.round(panes[2]!.size * 10) / 10
  localStorage.setItem('manuscript-left-size', String(leftSize.value))
  localStorage.setItem('manuscript-right-size', String(rightSize.value))
}

function toggleFocus() {
  focusMode.value = !focusMode.value
  localStorage.setItem('manuscript-focus-mode', focusMode.value ? '1' : '0')
}

function handleKeyboard(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
    event.preventDefault()
    void saveNow(true)
  }
  if (event.key === 'Escape' && focusMode.value) toggleFocus()
}

watch(leftVisible, (value) =>
  localStorage.setItem('manuscript-left-visible', value ? '1' : '0'),
)
watch(rightVisible, (value) =>
  localStorage.setItem('manuscript-right-visible', value ? '1' : '0'),
)
watch(fontSize, (value) => localStorage.setItem('manuscript-font-size', String(value)))
watch(lineHeight, (value) => localStorage.setItem('manuscript-line-height', String(value)))
watch(
  () => route.query.chapter,
  (value) => {
    const chapterId = typeof value === 'string' ? value : ''
    if (chapterId && chapterId !== activeChapterId.value) void openChapter(chapterId)
  },
)

onMounted(async () => {
  mediaQuery = window.matchMedia('(max-width: 900px)')
  updateMobile()
  mediaQuery.addEventListener('change', updateMobile)
  window.addEventListener('keydown', handleKeyboard)
  const chapterId = typeof route.query.chapter === 'string' ? route.query.chapter : ''
  await load(chapterId)
})

onBeforeUnmount(() => {
  mediaQuery?.removeEventListener('change', updateMobile)
  window.removeEventListener('keydown', handleKeyboard)
})
</script>

<template>
  <section class="manuscript-page" :class="{ 'focus-mode': focusMode }" v-loading="loading">
    <header class="manuscript-header">
      <div class="header-leading">
        <el-button
          v-if="!focusMode"
          :icon="ArrowRight"
          circle
          :type="leftVisible ? 'primary' : 'default'"
          aria-label="显示或隐藏章节目录"
          @click="mobile ? (mobileLeftOpen = true) : (leftVisible = !leftVisible)"
        />
        <div class="title-stack">
          <input
            :value="title"
            aria-label="章节标题"
            placeholder="未命名章节"
            @input="updateTitle(($event.target as HTMLInputElement).value)"
          />
          <span v-if="document">
            第 {{ document.chapter_id }} 章 · {{ document.plain_text.length }} 字
          </span>
        </div>
      </div>
      <div class="header-actions">
        <StatusBadge
          :label="SAVE_STATUS_LABELS[saveStatus]"
          :tone="saveStatusTone(saveStatus)"
          dot
        />
        <el-segmented
          v-model="preview"
          :options="[
            { label: '编辑', value: false },
            { label: '阅读', value: true },
          ]"
          aria-label="编辑或阅读模式"
        />
        <el-button
          :icon="FullScreen"
          :type="focusMode ? 'primary' : 'default'"
          @click="toggleFocus"
        >
          {{ focusMode ? '退出专注' : '专注' }}
        </el-button>
        <el-button
          v-if="!focusMode"
          :icon="ArrowLeft"
          circle
          :type="rightVisible ? 'primary' : 'default'"
          aria-label="显示或隐藏辅助栏"
          @click="mobile ? (mobileRightOpen = true) : (rightVisible = !rightVisible)"
        />
      </div>
    </header>

    <ErrorState
      v-if="loadError"
      title="正文中心暂时无法加载"
      :description="loadError"
      action-label="重试"
      @action="load(activeChapterId)"
    />
    <div v-else-if="!document" class="empty-manuscript">
      <el-empty description="还没有可编辑的章节">
        <el-button type="primary" @click="router.push('/outline')">返回策划中心</el-button>
      </el-empty>
    </div>

    <Splitpanes
      v-else-if="!mobile"
      class="manuscript-split"
      :dbl-click-splitter="false"
      @resized="updatePaneSizes"
    >
      <Pane
        v-if="leftVisible && !focusMode"
        class="manuscript-pane-left"
        :size="leftSize"
        :min-size="15"
        :max-size="28"
      >
        <ManuscriptChapterTree
          :chapters="workspace.chapters"
          :active-chapter-id="activeChapterId"
          @select="openChapter"
        />
      </Pane>
      <Pane :size="centerSize" :min-size="60">
        <ManuscriptEditor
          ref="editorRef"
          :content="content"
          :preview="preview"
          :font-size="fontSize"
          :line-height="lineHeight"
          @update="handleEditorUpdate"
          @selection="selection = $event"
        />
      </Pane>
      <Pane
        v-if="rightVisible && !focusMode"
        class="manuscript-pane-right"
        :size="rightSize"
        :min-size="17"
        :max-size="30"
      >
        <ManuscriptInspector
          ref="inspectorDesktopRef"
          :document="document"
          :context="workspace.context"
          :history="workspace.history"
          :ai-intent="aiIntent"
          :ai-suggestion="aiSuggestion"
          :ai-loading="aiLoading"
          :font-size="fontSize"
          :line-height="lineHeight"
          @confirm-ai="confirmAiIntent"
          @cancel-ai="cancelAi"
          @accept-ai="acceptAi"
          @preview-revision="revisionPreview = $event"
          @update-font-size="fontSize = $event"
          @update-line-height="lineHeight = $event"
        />
      </Pane>
    </Splitpanes>

    <ManuscriptEditor
      v-else-if="document"
      ref="editorRef"
      class="mobile-editor"
      :content="content"
      :preview="preview"
      :font-size="fontSize"
      :line-height="lineHeight"
      @update="handleEditorUpdate"
      @selection="selection = $event"
    />

    <div
      v-if="showSelectionMenu"
      class="selection-menu"
      :style="{ left: `${selection!.x}px`, top: `${selection!.y}px` }"
      role="toolbar"
      aria-label="AI 文本操作"
      @mousedown.prevent
    >
      <button @click="openAiIntent('rewrite')">改写</button>
      <button @click="openAiIntent('polish')">润色</button>
      <button @click="openAiIntent('shorten')">精简</button>
      <button @click="openAiIntent('expand')">扩写</button>
    </div>

    <button
      v-if="document && !preview && !aiIntent && !aiSuggestion"
      class="continue-button"
      type="button"
      @click="openAiIntent('continue')"
    >
      <MagicStick /> 续写建议
    </button>

    <el-drawer v-model="mobileLeftOpen" direction="ltr" size="84%" title="章节目录">
      <ManuscriptChapterTree
        :chapters="workspace.chapters"
        :active-chapter-id="activeChapterId"
        @select="openChapter"
      />
    </el-drawer>
    <el-drawer v-model="mobileRightOpen" direction="rtl" size="88%" title="正文辅助">
      <ManuscriptInspector
        ref="inspectorMobileRef"
        :document="document"
        :context="workspace.context"
        :history="workspace.history"
        :ai-intent="aiIntent"
        :ai-suggestion="aiSuggestion"
        :ai-loading="aiLoading"
        :font-size="fontSize"
        :line-height="lineHeight"
        @confirm-ai="confirmAiIntent"
        @cancel-ai="cancelAi"
        @accept-ai="acceptAi"
        @preview-revision="revisionPreview = $event"
        @update-font-size="fontSize = $event"
        @update-line-height="lineHeight = $event"
      />
    </el-drawer>

    <el-dialog
      :model-value="Boolean(conflictDocument)"
      title="发现另一个窗口的修改"
      width="520px"
      :close-on-click-modal="false"
      :show-close="false"
    >
      <p class="dialog-copy">
        服务器正文已更新到修订 {{ conflictDocument?.revision }}。本窗口内容仍保留，系统没有覆盖任何一方。
      </p>
      <template #footer>
        <el-button @click="useServerVersion">载入服务器版本</el-button>
        <el-button type="primary" @click="keepLocalAsNewRevision">保留本地并新建修订</el-button>
      </template>
    </el-dialog>

    <el-dialog
      :model-value="Boolean(revisionPreview)"
      @update:model-value="revisionPreview = $event ? revisionPreview : null"
      title="历史修订预览"
      width="min(820px, 92vw)"
    >
      <div v-if="revisionPreview" class="revision-compare">
        <section>
          <small>历史修订 {{ revisionPreview.revision }}</small>
          <h3>{{ revisionPreview.title }}</h3>
          <p>{{ revisionPreview.plain_text }}</p>
        </section>
        <section>
          <small>当前修订 {{ document?.revision }}</small>
          <h3>{{ document?.title }}</h3>
          <p>{{ document?.plain_text }}</p>
        </section>
      </div>
      <template #footer>
        <el-button @click="revisionPreview = null">关闭</el-button>
        <el-button type="primary" @click="restorePreviewedRevision">恢复为新的当前修订</el-button>
      </template>
    </el-dialog>

    <div v-if="saveError" class="save-error">{{ saveError }}</div>
  </section>
</template>

<style scoped>
.manuscript-page {
  position: relative;
  width: 100%;
  min-width: 0;
  height: 100%;
  min-height: 620px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--color-bg-canvas);
}
.manuscript-header {
  min-height: 68px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 8px 16px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-surface);
  z-index: 4;
}
.header-leading,
.header-actions {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}
.title-stack {
  min-width: 0;
  display: grid;
  gap: 3px;
}
.title-stack input {
  width: min(36vw, 440px);
  padding: 0;
  border: 0;
  outline: none;
  background: transparent;
  color: var(--color-text-strong);
  font-size: 17px;
  font-weight: 800;
}
.title-stack span {
  color: var(--color-text-muted);
  font-size: 10px;
}
.manuscript-split {
  flex: 1;
  min-height: 0;
}
:deep(.splitpanes__pane) { overflow: hidden; }
:deep(.splitpanes__splitter) {
  position: relative;
  width: 5px;
  background: var(--color-border-subtle);
}
:deep(.splitpanes__splitter::before) {
  content: '';
  position: absolute;
  inset: 0 -3px;
}
.empty-manuscript { flex: 1; display: grid; place-items: center; }
.selection-menu {
  position: fixed;
  z-index: 30;
  display: flex;
  transform: translate(-50%, -100%);
  padding: 5px;
  border: 1px solid var(--color-border);
  border-radius: 9px;
  background: var(--color-bg-elevated, var(--color-bg-surface));
  box-shadow: var(--shadow-lg);
}
.selection-menu button {
  padding: 6px 9px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--color-text);
  font-size: 11px;
  cursor: pointer;
}
.selection-menu button:hover {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.continue-button {
  position: absolute;
  right: calc(19% + 22px);
  bottom: 22px;
  z-index: 5;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: 99px;
  background: var(--color-bg-surface);
  color: var(--color-primary);
  box-shadow: var(--shadow-md);
  font-size: 11px;
  cursor: pointer;
}
.continue-button svg { width: 14px; }
.focus-mode .continue-button { right: 22px; }
.dialog-copy { color: var(--color-text); line-height: 1.7; }
.revision-compare {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.revision-compare section {
  min-height: 280px;
  max-height: 54vh;
  overflow: auto;
  padding: 15px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  background: var(--color-bg-surface-muted);
}
.revision-compare small { color: var(--color-text-muted); }
.revision-compare h3 { margin: 6px 0 14px; font-size: 14px; }
.revision-compare p {
  margin: 0;
  color: var(--color-text);
  font-family: "Noto Serif SC", "Songti SC", serif;
  font-size: 13px;
  line-height: 1.9;
  white-space: pre-wrap;
}
.save-error {
  position: absolute;
  left: 50%;
  bottom: 18px;
  z-index: 8;
  transform: translateX(-50%);
  padding: 8px 12px;
  border-radius: 8px;
  background: var(--color-danger-soft);
  color: var(--color-danger);
  font-size: 11px;
}
.mobile-editor { flex: 1; min-height: 0; }
@media (max-width: 1100px) {
  .header-actions :deep(.el-button span) { display: none; }
  .title-stack input { width: 31vw; }
  .continue-button { right: calc(19% + 14px); }
}
@media (max-width: 900px) {
  .manuscript-page { min-height: 520px; }
  .manuscript-header { min-height: 60px; padding-inline: 10px; }
  .title-stack input { width: 38vw; font-size: 14px; }
  .header-actions { gap: 5px; }
  .header-actions :deep(.el-segmented) { display: none; }
  .continue-button { right: 14px; bottom: 14px; }
  .revision-compare { grid-template-columns: 1fr; }
}
</style>
