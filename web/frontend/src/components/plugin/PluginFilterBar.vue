<script setup lang="ts">
import { Grid, List } from '@element-plus/icons-vue'
import { pluginTypes } from '../../utils/pluginManagerConfig'

const searchQuery = defineModel<string>('searchQuery', { required: true })
const selectedType = defineModel<string>('selectedType', { required: true })
const selectedStatus = defineModel<string>('selectedStatus', { required: true })
const viewMode = defineModel<'list' | 'card'>('viewMode', { default: 'list' })
</script>

<template>
  <div class="filter-bar panel">
    <el-input
      v-model="searchQuery"
      placeholder="搜索插件名称、描述..."
      clearable
      class="search-input"
    />
    <el-select v-model="selectedType" placeholder="插件类型" clearable class="filter-select">
      <el-option
        v-for="item in pluginTypes"
        :key="item.value"
        :label="item.label"
        :value="item.value"
      />
    </el-select>
    <el-select v-model="selectedStatus" placeholder="启用状态" clearable class="filter-select-sm">
      <el-option label="已启用" value="active" />
      <el-option label="已禁用" value="inactive" />
    </el-select>

    <div class="view-mode-toggle">
      <el-radio-group v-model="viewMode" size="default">
        <el-radio-button value="list">
          <el-icon><List /></el-icon>
          <span class="mode-text">窄行</span>
        </el-radio-button>
        <el-radio-button value="card">
          <el-icon><Grid /></el-icon>
          <span class="mode-text">卡片</span>
        </el-radio-button>
      </el-radio-group>
    </div>
  </div>
</template>

<style scoped>
.filter-bar {
  display: flex;
  gap: 12px;
  padding: 16px;
  align-items: center;
  flex-wrap: wrap;
}

.search-input {
  flex: 1;
  min-width: 200px;
}

.filter-select {
  width: 200px;
}

.filter-select-sm {
  width: 130px;
}

.view-mode-toggle {
  display: flex;
  align-items: center;
}

.mode-text {
  margin-left: 4px;
}
</style>