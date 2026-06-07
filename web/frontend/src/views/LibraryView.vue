<script setup lang="ts">
import { onMounted } from 'vue'
import { Document, Plus, Upload } from '@element-plus/icons-vue'
import EmptyStatePanel from '../components/EmptyStatePanel.vue'
import LibraryBookGrid from '../components/library/LibraryBookGrid.vue'
import LibraryDialogs from '../components/library/LibraryDialogs.vue'
import { useProjectStore } from '../stores/project'
import { useLibraryProjects, MAX_PINNED } from '../composables/useLibraryProjects'
import { useLibraryDescription } from '../composables/useLibraryDescription'
import { useLibraryCover } from '../composables/useLibraryCover'

const projectStore = useProjectStore()

const {
  searchQuery,
  pinningId,
  detailsVisible,
  selectedProject,
  exportingZip,
  fileInput,
  coverTimestamps,
  pinnedCount,
  displayedProjects,
  getCoverUrl,
  getCoverStyle,
  togglePin,
  openPendingMaintenance,
  openProject,
  openDetails,
  goCreate,
  handleDelete,
  handleRead,
  handleExportFormat,
  handleExportZip,
  triggerUpload,
  handleImportZip,
} = useLibraryProjects()

const {
  rewriteVisible,
  rewriteStyle,
  userPreference,
  rewriteLoading,
  rewrittenDesc,
  openDescriptionRewriter,
  handleRewrite,
  copyDescription,
  applyDescription,
} = useLibraryDescription({
  selectedProject,
  refreshProjects: () => projectStore.fetchProjects(),
})

const {
  coverManagerVisible,
  imageModels,
  selectedImageModel,
  coverPrompt,
  generatingPrompt,
  coverGenerating,
  cropImageSrc,
  cropperImg,
  scale,
  minScale,
  translateX,
  translateY,
  savingCover,
  fileInputCover,
  openCoverManager,
  handleSuggestCoverPrompt,
  handleGenerateCover,
  triggerCoverUpload,
  handleCoverFileChange,
  initCropper,
  handleMouseDown,
  handleMouseMove,
  handleMouseUp,
  handleTouchStart,
  handleTouchMove,
  handleSaveCover,
} = useLibraryCover({
  selectedProject,
  coverTimestamps,
  refreshProjects: () => projectStore.fetchProjects(),
})

onMounted(async () => {
  await projectStore.fetchProjects()
})

// template ref binding
void fileInput
</script>

<template>
  <section class="library-page">
    <header class="page-head">
      <div class="page-title-area">
        <h1>我的书库</h1>
        <p>选择项目继续创作，或用预设创建一本新小说。</p>
      </div>
      <div class="header-actions">
        <el-input
          v-if="projectStore.projects.length > 0"
          v-model="searchQuery"
          class="library-search"
          placeholder="搜索书名、题材、简介…"
          clearable
        />
        <el-button type="warning" plain :icon="Upload" @click="triggerUpload">导入项目包</el-button>
        <el-button type="primary" :icon="Plus" @click="goCreate">新建小说</el-button>
        <input
          ref="fileInput"
          type="file"
          accept=".zip"
          style="display: none"
          @change="handleImportZip"
        />
      </div>
    </header>

    <EmptyStatePanel
      v-if="projectStore.projects.length === 0"
      class="empty-library"
      :icon="Document"
      title="还没有小说项目"
      description="创建项目后即可进入多 Agent 工作台。"
      :actions="[
        { label: '导入项目包', type: 'warning', plain: true, icon: Upload, onClick: triggerUpload },
        { label: '新建小说', type: 'primary', icon: Plus, onClick: goCreate },
      ]"
    />

    <p
      v-if="projectStore.projects.length > 0 && searchQuery.trim()"
      class="search-hint"
    >
      共 {{ projectStore.projects.length }} 本，筛选 {{ displayedProjects.length }} 本
      <span v-if="pinnedCount > 0"> · 已置顶 {{ pinnedCount }}/{{ MAX_PINNED }}</span>
    </p>

    <div v-if="projectStore.projects.length > 0 && displayedProjects.length === 0" class="search-empty">
      <p>没有匹配「{{ searchQuery }}」的作品</p>
      <el-button text type="primary" @click="searchQuery = ''">清空搜索</el-button>
    </div>

    <LibraryBookGrid
      v-else-if="projectStore.projects.length > 0"
      :projects="displayedProjects"
      :pinning-id="pinningId"
      :get-cover-style="getCoverStyle"
      :on-open-project="openProject"
      :on-toggle-pin="togglePin"
      :on-open-pending-maintenance="openPendingMaintenance"
      :on-open-details="openDetails"
      :on-handle-read="handleRead"
      :on-handle-delete="handleDelete"
      :on-handle-export-format="handleExportFormat"
    />

    <LibraryDialogs
      v-model:details-visible="detailsVisible"
      v-model:rewrite-visible="rewriteVisible"
      v-model:cover-manager-visible="coverManagerVisible"
      v-model:rewrite-style="rewriteStyle"
      v-model:user-preference="userPreference"
      v-model:rewritten-desc="rewrittenDesc"
      v-model:selected-image-model="selectedImageModel"
      v-model:cover-prompt="coverPrompt"
      v-model:scale="scale"
      v-model:cropper-img="cropperImg"
      v-model:file-input-cover="fileInputCover"
      :selected-project="selectedProject"
      :exporting-zip="exportingZip"
      :rewrite-loading="rewriteLoading"
      :image-models="imageModels"
      :generating-prompt="generatingPrompt"
      :cover-generating="coverGenerating"
      :crop-image-src="cropImageSrc"
      :min-scale="minScale"
      :translate-x="translateX"
      :translate-y="translateY"
      :saving-cover="savingCover"
      :get-cover-url="getCoverUrl"
      :on-export-zip="handleExportZip"
      :on-open-cover-manager="openCoverManager"
      :on-copy-description="copyDescription"
      :on-open-description-rewriter="openDescriptionRewriter"
      :on-rewrite="handleRewrite"
      :on-apply-description="applyDescription"
      :on-suggest-cover-prompt="handleSuggestCoverPrompt"
      :on-generate-cover="handleGenerateCover"
      :on-trigger-cover-upload="triggerCoverUpload"
      :on-cover-file-change="handleCoverFileChange"
      :on-init-cropper="initCropper"
      :on-mouse-down="handleMouseDown"
      :on-mouse-move="handleMouseMove"
      :on-mouse-up="handleMouseUp"
      :on-touch-start="handleTouchStart"
      :on-touch-move="handleTouchMove"
      :on-save-cover="handleSaveCover"
    />
  </section>
</template>

<style scoped>
.library-page {
  display: grid;
  grid-template-rows: auto 1fr;
  align-content: start;
  gap: 16px;
  min-height: calc(100vh - 120px);
  padding: 40px 42px 46px;
  margin-top: 15px;
  background:
    repeating-linear-gradient(
      90deg,
      rgba(255, 255, 255, 0.34) 0 1px,
      rgba(186, 151, 102, 0.06) 1px 8px,
      rgba(255, 255, 255, 0.12) 8px 14px
    ),
    linear-gradient(135deg, #fbfaf6 0%, #f2eee6 100%);
  border-radius: 12px;
  border: 1px solid #e0d2bf;
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.58),
    inset 0 26px 42px rgba(255, 255, 255, 0.5),
    0 16px 34px rgba(82, 58, 34, 0.1);
  position: relative;
}

.library-search {
  width: 220px;
}

.header-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.search-hint {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--color-text-muted);
}

.search-empty {
  text-align: center;
  padding: 48px 20px;
  color: var(--color-text-muted);
  border: 1px dashed #cfd7e3;
  border-radius: 8px;
  background: var(--color-bg-surface-muted);
}

.search-empty p {
  margin: 0 0 12px;
}

.empty-library {
  min-height: 360px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 12px;
  border: 1px dashed #cfd7e3;
  border-radius: 8px;
  background: var(--color-bg-surface);
  color: #7b8494;
  z-index: 10;
}
</style>