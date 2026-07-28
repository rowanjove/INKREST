<script setup lang="ts">
import { Collection, Delete, Document } from '@element-plus/icons-vue'
import { assetMeta, assetNames, formatAssetSize, type AssetItem } from '../../utils/assetEditorConfig'

defineProps<{
  groupedAssets: { name: string; items: AssetItem[] }[]
  currentAssetName?: string
  selectedCustomAssets: string[]
  isAllCustomSelected: boolean
  isCustomIndeterminate: boolean
  onLoadAsset: (name: string) => void
  onToggleSelectAllCustom: (val: boolean) => void
  onToggleSelectAsset: (name: string) => void
  onBulkImportToTerminology: () => void
  onBulkDelete: () => void
  onContextCommand: (command: string, asset: AssetItem) => void
}>()
</script>

<template>
  <aside class="asset-list">
    <div v-for="group in groupedAssets" :key="group.name" class="asset-group">
      <div class="asset-group-title">
        <span>{{ group.name }}</span>
        <div v-if="group.name === '自定义资产'" class="custom-group-actions">
          <el-checkbox
            v-if="group.items.length"
            :model-value="isAllCustomSelected"
            :indeterminate="isCustomIndeterminate"
            @change="onToggleSelectAllCustom"
            style="margin-right: 8px; height: auto;"
          />
          <el-button
            v-if="selectedCustomAssets.length"
            size="small"
            type="primary"
            link
            @click="onBulkImportToTerminology"
          >
            导入名词解释({{ selectedCustomAssets.length }})
          </el-button>
          <el-button
            v-if="selectedCustomAssets.length"
            size="small"
            type="danger"
            link
            @click="onBulkDelete"
            style="margin-left: 8px;"
          >
            批量删除({{ selectedCustomAssets.length }})
          </el-button>
        </div>
        <em v-else>{{ group.items.length }}</em>
      </div>

      <div v-for="asset in group.items" :key="asset.name" class="asset-row-wrapper">
        <el-dropdown
          trigger="contextmenu"
          placement="bottom-start"
          :disabled="group.name !== '自定义资产'"
          style="width: 100%; display: block;"
          @command="(cmd: string) => onContextCommand(cmd, asset)"
        >
          <div
            class="asset-row"
            :class="{ active: currentAssetName === asset.name }"
            @click="onLoadAsset(asset.name)"
          >
            <el-checkbox
              v-if="group.name === '自定义资产'"
              :model-value="selectedCustomAssets.includes(asset.name)"
              @change="() => onToggleSelectAsset(asset.name)"
              @click.stop
              style="margin-right: 4px; height: auto;"
            />
            <span class="asset-row-icon" :class="assetMeta[asset.name]?.tone || 'gray'">
              <el-icon><component :is="assetMeta[asset.name]?.icon || Document" /></el-icon>
            </span>
            <span class="asset-row-main">
              <strong>{{ asset.label || assetNames[asset.name] || asset.name }}</strong>
              <small>{{ asset.path }}</small>
            </span>
            <span class="asset-row-size">{{ formatAssetSize(asset.size) }}</span>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="import_to_terminology" :icon="Collection">
                导入子设定 (名词解释)
              </el-dropdown-item>
              <el-dropdown-item command="delete_asset" :icon="Delete" style="color: #f56c6c;">
                删除资产
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.asset-list {
  padding: 8px;
  overflow: auto;
  background: var(--color-bg-surface);
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
}

.asset-group {
  display: grid;
  gap: 6px;
  margin-bottom: 12px;
}

.asset-group-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px 2px;
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 800;
}

.asset-group-title em {
  font-style: normal;
  color: var(--color-text-subtle);
}

.asset-row-wrapper {
  margin-bottom: 2px;
}

.asset-row {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  color: #1f2937;
  text-align: left;
  cursor: pointer;
  box-sizing: border-box;
}

.asset-row:hover,
.asset-row.active {
  background: var(--color-bg-surface-muted);
  border-color: #dbe2ea;
}

.asset-row.active {
  box-shadow: inset 3px 0 0 #c66f4f;
}

.asset-row-icon {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: #eef6fb;
  color: #2f6f90;
}

.asset-row-icon.blue { background: #eef6fb; color: #2f6f90; }
.asset-row-icon.green { background: #ecfdf5; color: #15803d; }
.asset-row-icon.purple { background: #f5f3ff; color: #6d4cc2; }
.asset-row-icon.orange { background: #fff4ee; color: #b65f3e; }
.asset-row-icon.gray { background: var(--color-bg-hover); color: var(--color-text-muted); }

.asset-row-main {
  min-width: 0;
  display: grid;
  gap: 2px;
  flex: 1;
}

.asset-row-main strong,
.asset-row-main small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.asset-row-main strong {
  font-size: 15px;
}

.asset-row-main small {
  color: #7b8494;
  font-size: 13px;
}

.asset-row-size {
  color: #7b8494;
  font-size: 13px;
  margin-left: auto;
  flex-shrink: 0;
}

.custom-group-actions {
  display: flex;
  align-items: center;
}
</style>