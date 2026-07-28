<script setup lang="ts">
import { defineAsyncComponent, inject, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Document, MagicStick, Plus, Upload } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { apiErrorMessage, importDemoProject } from '../api'
import PageShell from '../shared/ui/PageShell.vue'
import EmptyState from '../shared/ui/EmptyState.vue'
import LibraryBookGrid from '../components/library/LibraryBookGrid.vue'
import LibraryDialogs from '../components/library/LibraryDialogs.vue'
const StudioProductionBoard = defineAsyncComponent(
  () => import('../components/studio/StudioProductionBoard.vue'),
)
import { useProjectStore } from '../stores/project'
import { useLibraryProjects, MAX_PINNED } from '../composables/useLibraryProjects'
import { useLibraryDescription } from '../composables/useLibraryDescription'
import { useLibraryCover } from '../composables/useLibraryCover'

const router = useRouter()
const projectStore = useProjectStore()
const libraryTab = ref<'books' | 'studio'>('books')
const importingDemo = ref(false)
const openAppTour = inject<(() => void) | undefined>('openAppTour', undefined)

async function importDemo() {
  importingDemo.value = true
  try {
    const { data } = await importDemoProject()
    await projectStore.fetchProjects()
    await projectStore.fetchCurrent()
    ElMessage.success(
      data.status === 'existing' ? '示例书已打开，可进入工厂控制台体验' : '示例书已导入，可进入工厂控制台体验',
    )
    router.push('/workspace?focus=pipeline')
  } catch (error: unknown) {
    ElMessage.error(apiErrorMessage(error, '示例书导入失败'))
  } finally {
    importingDemo.value = false
  }
}

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
  handleRename,
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
  <PageShell
    title="我的书库"
    description="选择作品继续创作，或切换到制片看板查看全部项目的生产状态。"
    eyebrow="作品"
    data-tour="library-header"
  >
    <template #actions>
      <div class="header-actions">
        <el-input
          v-if="projectStore.projects.length > 0"
          v-model="searchQuery"
          class="library-search"
          placeholder="搜索书名、题材、简介…"
          clearable
        />
        <el-button v-if="openAppTour" text type="primary" @click="openAppTour()">新手引导</el-button>
        <el-button
          v-if="projectStore.projects.length === 0"
          type="primary"
          plain
          :icon="MagicStick"
          :loading="importingDemo"
          @click="importDemo"
        >
          导入示例书
        </el-button>
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
    </template>

    <el-tabs v-model="libraryTab" class="library-tabs">
      <el-tab-pane label="书库" name="books" />
      <el-tab-pane label="制片看板" name="studio" />
    </el-tabs>

    <StudioProductionBoard v-if="libraryTab === 'studio'" />

    <template v-else>
    <EmptyState
      v-if="projectStore.projects.length === 0"
      class="empty-library"
      title="书库还是空的"
      description="可以导入示例书熟悉工作流，也可以直接创建自己的第一部作品。"
    >
      <template #icon><el-icon><Document /></el-icon></template>
      <template #actions>
        <el-button type="primary" :loading="importingDemo" @click="importDemo">导入示例书</el-button>
        <el-button type="success" plain @click="goCreate">新建作品</el-button>
        <el-button plain @click="triggerUpload">导入项目包</el-button>
      </template>
    </EmptyState>

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
      :on-rename="handleRename"
      :on-handle-read="handleRead"
      :on-handle-delete="handleDelete"
      :on-handle-export-format="handleExportFormat"
    />

    </template>

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
  </PageShell>
</template>

<style scoped>
.library-tabs {
  margin-top: -4px;
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
  min-height: 320px;
}
</style>
