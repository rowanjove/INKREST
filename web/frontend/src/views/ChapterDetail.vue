<script setup lang="ts">
import ChapterDetailAlerts from '../components/chapter/ChapterDetailAlerts.vue'
import ChapterDetailHeader from '../components/chapter/ChapterDetailHeader.vue'
import ChapterDetailTabs from '../components/chapter/ChapterDetailTabs.vue'
import ChapterDetailEditDialog from '../components/chapter/ChapterDetailEditDialog.vue'
import { useChapterDetail } from '../composables/useChapterDetail'

const {
  chapter,
  activeTab,
  loadError,
  rewriting,
  resumingAudit,
  rerunningGate,
  externalStatus,
  copying,
  editDialogVisible,
  savingEdit,
  editForm,
  hasFinalText,
  hasStateUpdates,
  stateChangeCount,
  isQualityBlocked,
  resumableFrom,
  wordStatusLabel,
  parseMarkdown,
  startEdit,
  handleSaveEdit,
  handleCopyFullText,
  goWriter,
  handleRerunGate,
  saveExternalStatus,
  handleResumeAudit,
  openUnifiedGateTab,
  handleRewrite,
  goBack,
} = useChapterDetail()
</script>

<template>
  <ChapterDetailAlerts
    :load-error="loadError"
    :chapter="chapter"
    :is-quality-blocked="isQualityBlocked"
    :resumable-from="resumableFrom"
    :resuming-audit="resumingAudit"
    :rerunning-gate="rerunningGate"
    :copying="copying"
    @go-writer="goWriter"
    @handle-resume-audit="handleResumeAudit"
    @handle-rerun-gate="handleRerunGate"
    @open-unified-gate-tab="openUnifiedGateTab"
    @handle-copy-full-text="handleCopyFullText"
  />

  <div v-if="chapter" class="chapter-detail-page">
    <ChapterDetailHeader
      :chapter="chapter"
      :external-status="externalStatus"
      :has-final-text="hasFinalText"
      :word-status-label="wordStatusLabel"
      :copying="copying"
      :rewriting="rewriting"
      @go-back="goBack"
      @save-external-status="saveExternalStatus"
      @handle-copy-full-text="handleCopyFullText"
      @start-edit="startEdit"
      @handle-rewrite="handleRewrite"
    />

    <ChapterDetailTabs
      v-model:active-tab="activeTab"
      :chapter="chapter"
      :is-quality-blocked="isQualityBlocked"
      :has-state-updates="hasStateUpdates"
      :state-change-count="stateChangeCount"
      :parse-markdown="parseMarkdown"
    />

    <ChapterDetailEditDialog
      v-model:edit-dialog-visible="editDialogVisible"
      :saving-edit="savingEdit"
      :edit-form="editForm"
      @save-edit="handleSaveEdit"
    />
  </div>
  <el-skeleton v-else :rows="12" animated />
</template>

<style scoped>
.chapter-detail-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
</style>