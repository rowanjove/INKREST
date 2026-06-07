<script setup lang="ts">
import { pluginTypes } from '../../utils/pluginManagerConfig'

const searchQuery = defineModel<string>('searchQuery', { required: true })
const selectedType = defineModel<string>('selectedType', { required: true })
const selectedStatus = defineModel<string>('selectedStatus', { required: true })
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
  </div>
</template>

<style scoped>
.filter-bar {
  display: flex;
  gap: 12px;
  padding: 16px;
  align-items: center;
}

.search-input {
  flex: 1;
}

.filter-select {
  width: 240px;
}

.filter-select-sm {
  width: 140px;
}
</style>