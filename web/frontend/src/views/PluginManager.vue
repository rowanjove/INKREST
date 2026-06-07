<script setup lang="ts">
import { Refresh, QuestionFilled, Upload } from '@element-plus/icons-vue'
import PluginAuthorHelpDialog from '../components/PluginAuthorHelpDialog.vue'
import PluginMetricsCards from '../components/plugin/PluginMetricsCards.vue'
import PluginFilterBar from '../components/plugin/PluginFilterBar.vue'
import PluginGrid from '../components/plugin/PluginGrid.vue'
import PluginManagerDialogs from '../components/plugin/PluginManagerDialogs.vue'
import { usePluginManager } from '../composables/usePluginManager'

const {
  loading,
  untrustedPlugins,
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
  filteredPlugins,
  totalCount,
  activeCount,
  handleTrust,
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
        <h1>🧩 插件生态管理</h1>
        <p>扩展您的创作环境，切换丰富的底层策略、质量保障以及格式导出功能。</p>
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

    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="新手可从官方示例插件开始"
      style="margin-bottom: 16px"
    >
      复制 <code>plugins/examples/</code> 下的 <code>hello_guard.py</code> 到 <code>plugins/</code> 后启用。
      详见仓库 <code>plugins/examples/README.md</code>。
    </el-alert>

    <el-alert
      v-if="untrustedPlugins.length"
      title="发现尚未信任的本地插件"
      type="warning"
      :closable="false"
      show-icon
      style="margin-bottom: 16px"
    >
      <template #default>
        <span>这些插件在信任前不会执行：</span>
        <el-button
          v-for="name in untrustedPlugins"
          :key="name"
          size="small"
          type="warning"
          plain
          style="margin-left: 8px"
          @click="handleTrust(name)"
        >
          信任 {{ name }}
        </el-button>
      </template>
    </el-alert>

    <PluginMetricsCards :total-count="totalCount" :active-count="activeCount" />

    <PluginFilterBar
      v-model:search-query="searchQuery"
      v-model:selected-type="selectedType"
      v-model:selected-status="selectedStatus"
    />

    <PluginGrid
      :plugins="filteredPlugins"
      :loading="loading"
      :on-show-detail="showDetail"
      :on-show-config="showConfig"
      :on-delete="handleDelete"
      :on-toggle="handleToggle"
    />

    <PluginAuthorHelpDialog v-model:visible="helpDialogVisible" />

    <PluginManagerDialogs
      v-model:detail-dialog-visible="detailDialogVisible"
      v-model:config-dialog-visible="configDialogVisible"
      v-model:install-dialog-visible="installDialogVisible"
      v-model:config-form="configForm"
      v-model:config-json-text="configJsonText"
      v-model:install-drag-over="installDragOver"
      :selected-plugin="selectedPlugin"
      :config-json-mode="configJsonMode"
      :install-uploading="installUploading"
      :install-file="installFile"
      :get-type-label="getTypeLabel"
      :on-install-drop="onInstallDrop"
      :on-install-file-change="onInstallFileChange"
      :on-submit-install="submitInstall"
      :on-save-config="saveConfig"
    />
  </div>
</template>

<style scoped>
.plugin-manager-view {
  display: grid;
  gap: 20px;
}
</style>