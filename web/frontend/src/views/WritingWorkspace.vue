<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Expand } from '@element-plus/icons-vue'
import WritingChapterSidebar from '../components/writing/WritingChapterSidebar.vue'
import WritingEditorMain from '../components/writing/WritingEditorMain.vue'
import WritingRightSidebar from '../components/writing/WritingRightSidebar.vue'
import WritingWorkspaceDialogs from '../components/writing/WritingWorkspaceDialogs.vue'
import { useWritingVisualSettings } from '../composables/useWritingVisualSettings'
import { useWritingChapterEditor } from '../composables/useWritingChapterEditor'
import { useWritingVersions } from '../composables/useWritingVersions'
import { useWritingScrapbook } from '../composables/useWritingScrapbook'
import { useWritingEditorAssist } from '../composables/useWritingEditorAssist'
import { useWritingAiWrite } from '../composables/useWritingAiWrite'
import { useWritingSnapshots } from '../composables/useWritingSnapshots'
import { useWritingPlatformFeedback } from '../composables/useWritingPlatformFeedback'

const route = useRoute()

const editorRef = ref<HTMLTextAreaElement | null>(null)
const assetSidebarRef = ref<{ refreshAssets?: () => void } | null>(null)
const rightTab = ref<'assets' | 'scrapbook' | 'feedback' | 'golden'>('assets')
const sidebarCollapsed = ref(false)
const rightSidebarCollapsed = ref(false)

let fetchScrapbookImpl: () => Promise<void> = async () => {}
let resetAssistImpl: () => void = () => {}
let adjustTextareaHeightImpl: () => void = () => {}

const {
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
} = useWritingChapterEditor({
  editorRef,
  assetSidebarRef,
  rightTab,
  adjustTextareaHeight: () => adjustTextareaHeightImpl(),
  onChapterLoadStart: () => resetAssistImpl(),
  fetchScrapbook: () => fetchScrapbookImpl(),
})

const {
  writeTheme,
  writeFontSize,
  writeLineHeight,
  writeIndent,
  writeTitleCenter,
  adjustTextareaHeight,
  loadVisualSettings,
} = useWritingVisualSettings({ editorRef, editorText })
adjustTextareaHeightImpl = adjustTextareaHeight

const {
  scrapbookList,
  scrapbookQuery,
  loadingScrapbook,
  fetchScrapbook,
  copyScrapbookText,
  insertScrapbookText,
} = useWritingScrapbook({
  activeChapterId,
  editorText,
  editorRef,
  adjustTextareaHeight,
  rightTab,
})
fetchScrapbookImpl = fetchScrapbook

const {
  compareDialogOpen,
  diffChunks,
  loadingDiff,
  compareVersionId,
  handleVersionChange,
  handleCreateVersion,
  handleActivateVersion,
  handleDeleteVersion,
  handleOpenCompare,
} = useWritingVersions({
  activeChapterId,
  editorText,
  versionsList,
  activeVersionId,
  activeVersion,
  adjustTextareaHeight,
  loadChapter,
  fetchChapters,
  fetchScrapbook,
})

const {
  showBubble,
  bubbleX,
  bubbleY,
  selectedText,
  expandResult,
  showExpandDialog,
  resetAssistState,
  handleKeyDown,
  handleTextSelection,
  handleAcceptRewrite,
  handleTriggerExpand,
  handleAcceptExpand,
} = useWritingEditorAssist({
  editorRef,
  editorText,
  activeChapterId,
  currentChapter,
  handleSave,
})
resetAssistImpl = resetAssistState

const {
  writing,
  writeDialogOpen,
  chapterGoalForWrite,
  stopAiWritePolling,
  handleTriggerWrite,
  handleStartAiWrite,
  handleAutoFormat,
} = useWritingAiWrite({
  activeChapterId,
  editorText,
  loadingEditor,
  loadChapter,
  fetchChapters,
  adjustTextareaHeight,
  writeTitleCenter,
  writeIndent,
})

const {
  timeMachineOpen,
  snapshotsList,
  loadingSnapshots,
  previewingSnapshot,
  showPreviewDialog,
  handleOpenTimeMachine,
  handleManualSnapshot,
  handlePreviewSnapshot,
  handleRollback,
} = useWritingSnapshots({
  activeChapterId,
  currentChapter,
  loadChapter,
  fetchChapters,
  handleSave,
})

const {
  activePlatform,
  activePlatformLabel,
  platformsList,
  feedbackList,
  loadingFeedback,
  loadingGolden,
  feedbackForm,
  goldenCheckResult,
  initProjectPlatformAndFeedback,
  handlePlatformChange,
  submitFeedback,
  runGoldenCheck,
  handleGoldenRewrite,
} = useWritingPlatformFeedback({
  activeChapterId,
  loadingEditor,
})

let autoSaveTimer: number | null = null

function setEditorRef(el: HTMLTextAreaElement | null) {
  editorRef.value = el
}

function setAssetSidebarRef(el: { refreshAssets?: () => void } | null) {
  assetSidebarRef.value = el
}

watch(
  () => route.query.chapter,
  (chapter) => {
    void openChapterFromQuery(chapter)
  },
)

onMounted(async () => {
  loadVisualSettings()
  await fetchChapters()
  await openChapterFromQuery(route.query.chapter)
  void initProjectPlatformAndFeedback()
  autoSaveTimer = window.setInterval(() => {
    void handleSave(true)
  }, 60000)
})

onBeforeUnmount(() => {
  stopAiWritePolling()
  if (autoSaveTimer) {
    window.clearInterval(autoSaveTimer)
  }
})
</script>

<template>
  <div class="workspace-page-container writing-page-shell">
    <WritingChapterSidebar
      v-model:collapsed="sidebarCollapsed"
      :chapters-list="chaptersList"
      :active-chapter-id="activeChapterId"
      :on-load-chapter="loadChapter"
      :on-open-create-chapter="handleOpenCreateChapter"
      :on-delete-chapter="handleDeleteChapter"
    />

    <el-button
      v-if="sidebarCollapsed"
      type="text"
      :icon="Expand"
      class="left-sidebar-expand"
      @click="sidebarCollapsed = false"
      title="展开目录"
    />

    <WritingEditorMain
      :set-editor-ref="setEditorRef"
      v-model:editor-text="editorText"
      v-model:write-theme="writeTheme"
      v-model:write-font-size="writeFontSize"
      v-model:write-line-height="writeLineHeight"
      v-model:write-indent="writeIndent"
      v-model:write-title-center="writeTitleCenter"
      :loading-editor="loadingEditor"
      :current-chapter="currentChapter"
      :platforms-list="platformsList"
      :active-platform="activePlatform"
      :active-platform-label="activePlatformLabel"
      :versions-list="versionsList"
      :active-version="activeVersion"
      :saving="saving"
      :on-platform-change="handlePlatformChange"
      :on-version-change="handleVersionChange"
      :on-open-compare="handleOpenCompare"
      :on-delete-version="handleDeleteVersion"
      :on-create-version="handleCreateVersion"
      :on-activate-version="handleActivateVersion"
      :on-auto-format="handleAutoFormat"
      :on-manual-snapshot="handleManualSnapshot"
      :on-save="() => handleSave()"
      :on-force-refresh="handleForceRefresh"
      :on-open-time-machine="handleOpenTimeMachine"
      :on-trigger-write="handleTriggerWrite"
      :on-key-down="handleKeyDown"
      :on-text-selection="handleTextSelection"
      :on-adjust-textarea-height="adjustTextareaHeight"
    />

    <el-button
      v-if="rightSidebarCollapsed"
      class="right-sidebar-expand"
      :icon="Expand"
      circle
      title="展开辅助栏"
      @click="rightSidebarCollapsed = false"
    />

    <WritingRightSidebar
      v-model:collapsed="rightSidebarCollapsed"
      v-model:right-tab="rightTab"
      v-model:scrapbook-query="scrapbookQuery"
      v-model:feedback-form="feedbackForm"
      :set-asset-sidebar-ref="setAssetSidebarRef"
      :active-chapter-id="activeChapterId"
      :current-chapter="currentChapter"
      :chapters-list="chaptersList"
      :scrapbook-list="scrapbookList"
      :loading-scrapbook="loadingScrapbook"
      :loading-feedback="loadingFeedback"
      :loading-golden="loadingGolden"
      :feedback-list="feedbackList"
      :golden-check-result="goldenCheckResult"
      :on-fetch-scrapbook="fetchScrapbook"
      :on-copy-scrapbook-text="copyScrapbookText"
      :on-insert-scrapbook-text="insertScrapbookText"
      :on-submit-feedback="submitFeedback"
      :on-run-golden-check="runGoldenCheck"
      :on-golden-rewrite="handleGoldenRewrite"
    />

    <WritingWorkspaceDialogs
      v-model:show-bubble="showBubble"
      v-model:show-expand-dialog="showExpandDialog"
      v-model:expand-result="expandResult"
      v-model:time-machine-open="timeMachineOpen"
      v-model:show-preview-dialog="showPreviewDialog"
      v-model:compare-dialog-open="compareDialogOpen"
      v-model:write-dialog-open="writeDialogOpen"
      v-model:chapter-goal-for-write="chapterGoalForWrite"
      :bubble-x="bubbleX"
      :bubble-y="bubbleY"
      :selected-text="selectedText"
      :active-chapter-id="activeChapterId"
      :current-chapter="currentChapter"
      :snapshots-list="snapshotsList"
      :loading-snapshots="loadingSnapshots"
      :previewing-snapshot="previewingSnapshot"
      :versions-list="versionsList"
      :compare-version-id="compareVersionId"
      :diff-chunks="diffChunks"
      :loading-diff="loadingDiff"
      :writing="writing"
      :on-accept-rewrite="handleAcceptRewrite"
      :on-trigger-expand="handleTriggerExpand"
      :on-accept-expand="handleAcceptExpand"
      :on-manual-snapshot="handleManualSnapshot"
      :on-preview-snapshot="handlePreviewSnapshot"
      :on-rollback="handleRollback"
      :on-activate-version="handleActivateVersion"
      :on-start-ai-write="handleStartAiWrite"
    />
  </div>
</template>

<style scoped>
.workspace-page-container {
  display: flex;
  width: 100%;
  height: 100%;
  box-sizing: border-box;
  overflow: hidden;
}

.left-sidebar-expand {
  align-self: flex-start;
  margin: 30px 0 0 8px;
  font-size: 18px;
  padding: 0;
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.right-sidebar-expand {
  align-self: center;
  margin: 0 8px;
  flex-shrink: 0;
}
</style>