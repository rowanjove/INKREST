<script setup lang="ts">
import { ref, watch } from 'vue'
import { Refresh, QuestionFilled, Upload } from '@element-plus/icons-vue'
import PluginAuthorHelpDialog from '../components/PluginAuthorHelpDialog.vue'
import PluginMetricsCards from '../components/plugin/PluginMetricsCards.vue'
import PluginFilterBar from '../components/plugin/PluginFilterBar.vue'
import PluginGrid from '../components/plugin/PluginGrid.vue'
import PluginManagerDialogs from '../components/plugin/PluginManagerDialogs.vue'
import { usePluginManager } from '../composables/usePluginManager'

const viewMode = ref<'list' | 'card'>(
  (localStorage.getItem('inkrest_plugin_view_mode') as 'list' | 'card') || 'list'
)

watch(viewMode, (newVal) => {
  localStorage.setItem('inkrest_plugin_view_mode', newVal)
})

const {
  loading,
  searchQuery,
  selectedType,
  selectedStatus,
  detailDialogVisible,
  configDialogVisible,
  installDialogVisible,
  selectedPlugin,
  configForm,
  configJsonMode,
  configJsonText,
  installUploading,
  installDragOver,
  installFile,
  helpDialogVisible,
  trustDialogVisible,
  trustTarget,
  trustAcknowledged,
  localCodeAcknowledged,
  trustLoading,
  filteredPlugins,
  totalCount,
  activeCount,
  handleTrust,
  confirmTrust,
  handleScan,
  handleToggle,
  openInstallDialog,
  onInstallDrop,
  onInstallFileChange,
  submitInstall,
  handleDelete,
  showDetail,
  showConfig,
  saveConfig,
  getTypeLabel,
} = usePluginManager()
</script>

<template>
  <div class="plugin-manager-view">
    <header class="page-head">
      <div class="page-title-area">
        <div class="title-with-metrics">
          <h1>扩展中心</h1>
          <PluginMetricsCards :total-count="totalCount" :active-count="activeCount" />
        </div>
        <p>集中检查插件来源、内容摘要、运行权限与启用状态。</p>
      </div>
      <div class="head-actions">
        <el-tooltip content="插件格式与开发说明" placement="bottom">
          <el-button :icon="QuestionFilled" circle @click="helpDialogVisible = true" />
        </el-tooltip>
        <el-button :icon="Upload" type="success" @click="openInstallDialog">载入插件</el-button>
        <el-button :icon="Refresh" type="primary" :loading="loading" @click="handleScan">
          重新扫描
        </el-button>
      </div>
    </header>

    <PluginFilterBar
      v-model:search-query="searchQuery"
      v-model:selected-type="selectedType"
      v-model:selected-status="selectedStatus"
      v-model:view-mode="viewMode"
    />

    <PluginGrid
      :plugins="filteredPlugins"
      :loading="loading"
      :view-mode="viewMode"
      :on-show-detail="showDetail"
      :on-show-config="showConfig"
      :on-delete="handleDelete"
      :on-toggle="handleToggle"
      :on-trust="handleTrust"
    />

    <PluginAuthorHelpDialog v-model:visible="helpDialogVisible" />

    <PluginManagerDialogs
      v-model:detail-dialog-visible="detailDialogVisible"
      v-model:config-dialog-visible="configDialogVisible"
      v-model:install-dialog-visible="installDialogVisible"
      v-model:trust-dialog-visible="trustDialogVisible"
      v-model:trust-acknowledged="trustAcknowledged"
      v-model:local-code-acknowledged="localCodeAcknowledged"
      v-model:config-form="configForm"
      v-model:config-json-text="configJsonText"
      v-model:install-drag-over="installDragOver"
      :selected-plugin="selectedPlugin"
      :config-json-mode="configJsonMode"
      :install-uploading="installUploading"
      :install-file="installFile"
      :trust-target="trustTarget"
      :trust-loading="trustLoading"
      :get-type-label="getTypeLabel"
      :on-install-drop="onInstallDrop"
      :on-install-file-change="onInstallFileChange"
      :on-submit-install="submitInstall"
      :on-save-config="saveConfig"
      :on-confirm-trust="confirmTrust"
    />
  </div>
</template>

<style scoped>
.plugin-manager-view {
  display: grid;
  gap: 20px;
}

.title-with-metrics {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.title-with-metrics h1 {
  margin: 0;
}
</style>
