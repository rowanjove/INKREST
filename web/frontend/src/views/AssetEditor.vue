<script setup lang="ts">
import { onMounted } from 'vue'
import { FolderOpened, MagicStick, Plus } from '@element-plus/icons-vue'
import AssetListSidebar from '../components/asset/AssetListSidebar.vue'
import AssetEditorPanel from '../components/asset/AssetEditorPanel.vue'
import AssetEditorDialogs from '../components/asset/AssetEditorDialogs.vue'
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
  <section class="asset-editor">
    <header class="page-head">
      <div class="page-title-area">
        <h1>资产编辑</h1>
        <p>维护角色、世界观、规则等项目素材；可手写、新增，也可让 AI 批量生成。</p>
      </div>
      <div class="head-actions">
        <el-button :icon="FolderOpened" @click="loadAssets">刷新</el-button>
        <el-button :icon="Plus" @click="createDialogVisible = true">新增资产</el-button>
        <el-button type="primary" :icon="MagicStick" @click="openGenerateDialog">AI 生成</el-button>
      </div>
    </header>

    <el-alert v-if="loadError" :title="loadError" type="warning" show-icon class="error-bar" />

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
  display: grid;
  gap: 18px;
}

.error-bar {
  border-radius: 8px;
}

.asset-layout {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 16px;
  min-height: calc(100vh - 210px);
}

@media (max-width: 980px) {
  .asset-layout {
    grid-template-columns: 1fr;
  }
}
</style>