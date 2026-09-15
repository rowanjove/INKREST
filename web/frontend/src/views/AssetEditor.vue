<script setup lang="ts">
import { onMounted } from 'vue'
import { FolderOpened, MagicStick, Plus } from '@element-plus/icons-vue'
import AssetListSidebar from '../components/asset/AssetListSidebar.vue'
import AssetEditorPanel from '../components/asset/AssetEditorPanel.vue'
import AssetEditorDialogs from '../components/asset/AssetEditorDialogs.vue'
import PlanningSectionNav from '../components/planning/PlanningSectionNav.vue'
import PlanningWorkspaceHeader from '../components/planning/PlanningWorkspaceHeader.vue'
import { useAssetEditor } from '../composables/useAssetEditor'

const {
  currentAsset,
  editContent,
  showAssetSource,
  saving,
  loading,
  loadError,
  createDialogVisible,
  generateDialogVisible,
  creating,
  generating,
  createForm,
  generateForm,
  addTermDialogOpen,
  addTermForm,
  selectedCustomAssets,
  selectedAssetType,
  currentTitle,
  groupedAssets,
  currentMeta,
  isMarkdownAsset,
  supportsAssetSource,
  contentBlocks,
  isAllCustomSelected,
  isCustomIndeterminate,
  loadAsset,
  loadAssets,
  handleSave,
  openAddTermDialog,
  handleAddTerm,
  handleCreate,
  openGenerateDialog,
  handleGenerate,
  handleToggleSelectAllCustom,
  handleToggleSelectAsset,
  handleBulkImportToTerminology,
  handleBulkDelete,
  handleContextCommand,
} = useAssetEditor()

onMounted(loadAssets)
</script>

<template>
  <section class="planning-page asset-editor">
    <PlanningWorkspaceHeader
      eyebrow="策划中心"
      title="素材资产"
      description="维护人物、世界、规则与自定义素材，在生产前补齐故事设定。"
    >
      <template #actions>
        <el-button :icon="FolderOpened" @click="loadAssets">刷新</el-button>
        <el-button :icon="Plus" @click="createDialogVisible = true">新增资产</el-button>
        <el-button type="primary" :icon="MagicStick" @click="openGenerateDialog">AI 生成</el-button>
      </template>
    </PlanningWorkspaceHeader>

    <PlanningSectionNav />

    <el-alert v-if="loadError" :title="loadError" type="warning" show-icon class="error-bar" />

    <div class="asset-content">
      <div class="asset-layout">
        <AssetListSidebar
        :grouped-assets="groupedAssets"
        :current-asset-name="currentAsset?.name"
        :selected-custom-assets="selectedCustomAssets"
        :is-all-custom-selected="isAllCustomSelected"
        :is-custom-indeterminate="isCustomIndeterminate"
        :on-load-asset="loadAsset"
        :on-toggle-select-all-custom="handleToggleSelectAllCustom"
        :on-toggle-select-asset="handleToggleSelectAsset"
        :on-bulk-import-to-terminology="handleBulkImportToTerminology"
        :on-bulk-delete="handleBulkDelete"
        :on-context-command="handleContextCommand"
      />

        <AssetEditorPanel
        v-model:edit-content="editContent"
        v-model:show-asset-source="showAssetSource"
        :loading="loading"
        :saving="saving"
        :current-asset="currentAsset"
        :current-title="currentTitle"
        :current-meta="currentMeta"
        :supports-asset-source="supportsAssetSource"
        :is-markdown-asset="isMarkdownAsset"
        :content-blocks="contentBlocks"
        @save="handleSave"
        @open-add-term="openAddTermDialog"
        />
      </div>
    </div>

    <AssetEditorDialogs
      v-model:create-dialog-visible="createDialogVisible"
      v-model:generate-dialog-visible="generateDialogVisible"
      v-model:add-term-dialog-open="addTermDialogOpen"
      v-model:create-form="createForm"
      v-model:generate-form="generateForm"
      v-model:add-term-form="addTermForm"
      :creating="creating"
      :generating="generating"
      :selected-asset-type="selectedAssetType"
      :on-create="handleCreate"
      :on-generate="handleGenerate"
      :on-add-term="handleAddTerm"
    />
  </section>
</template>

<style scoped>
.asset-editor {
  min-width: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--color-bg-canvas);
}

.error-bar {
  border-radius: 0;
}

.asset-content {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: var(--space-5);
  background: var(--color-bg-page);
}

.asset-layout {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 16px;
  min-height: 620px;
}

@media (max-width: 980px) {
  .asset-layout {
    grid-template-columns: 1fr;
  }
}
</style>
