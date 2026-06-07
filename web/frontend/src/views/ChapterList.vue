<script setup lang="ts">
import ChapterListTable from '../components/chapter/ChapterListTable.vue'
import ChapterRepairDialog from '../components/chapter/ChapterRepairDialog.vue'
import { useChapterList } from '../composables/useChapterList'

const {
  router,
  tasksStore,
  pipelineAlerts,
  chapters,
  deletingId,
  copyingId,
  gateRerunId,
  searchQuery,
  selectedStatus,
  currentPage,
  pageSize,
  repairDialogVisible,
  repairForm,
  repairing,
  suggestingGoal,
  filteredChapters,
  paginatedChapters,
  handleSuggestGoal,
  goWriter,
  isGateBlockedChapter,
  rerunGateOnly,
  openRepairDialog,
  submitRepair,
  copyChapterTitle,
  copyChapterBody,
  confirmDelete,
  getRiskTagType,
} = useChapterList()
</script>

<template>
  <section class="chapters-page">
    <ChapterListTable
      v-model:search-query="searchQuery"
      v-model:selected-status="selectedStatus"
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :router="router"
      :tasks-store="tasksStore"
      :pipeline-alerts="pipelineAlerts"
      :chapters="chapters"
      :deleting-id="deletingId"
      :copying-id="copyingId"
      :gate-rerun-id="gateRerunId"
      :filtered-chapters="filteredChapters"
      :paginated-chapters="paginatedChapters"
      :is-gate-blocked-chapter="isGateBlockedChapter"
      :get-risk-tag-type="getRiskTagType"
      :on-rerun-gate-only="rerunGateOnly"
      :on-go-writer="goWriter"
      :on-copy-chapter-title="copyChapterTitle"
      :on-copy-chapter-body="copyChapterBody"
      :on-confirm-delete="confirmDelete"
      :on-open-repair-dialog="openRepairDialog"
    />

    <ChapterRepairDialog
      v-model:repair-dialog-visible="repairDialogVisible"
      :tasks-store="tasksStore"
      :repair-form="repairForm"
      :repairing="repairing"
      :suggesting-goal="suggestingGoal"
      :on-suggest-goal="handleSuggestGoal"
      :on-submit-repair="submitRepair"
    />
  </section>
</template>

<style scoped>
.chapters-page {
  display: grid;
  gap: 20px;
}
</style>