<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  artifacts: Array<Record<string, any>>
}>()

const rows = computed(() => props.artifacts || [])

const tagType = (status: string) => {
  if (status === 'authoritative') return 'success'
  if (status === 'reference') return 'warning'
  if (status === 'stale') return 'danger'
  return 'info'
}
</script>

<template>
  <div class="artifact-status-panel">
    <div class="panel-head">
      <strong>磁盘产物可信度</strong>
      <span class="panel-hint">质量阻断时：绿色可信、橙色仅供参考、红色可能过期</span>
    </div>
    <el-table :data="rows" size="small" stripe class="artifact-table">
      <el-table-column prop="label" label="产物" min-width="120" />
      <el-table-column prop="path" label="路径" min-width="180" show-overflow-tooltip />
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="tagType(row.status)" size="small" effect="plain">
            {{ row.status_label || row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="note" label="说明" min-width="200" show-overflow-tooltip />
    </el-table>
  </div>
</template>

<style scoped>
.artifact-status-panel {
  background: var(--color-bg-surface);
  border: 1px solid var(--border-light);
  border-radius: 10px;
  padding: 14px;
}

.panel-head {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  align-items: baseline;
  margin-bottom: 12px;
}

.panel-hint {
  font-size: 12px;
  color: #909399;
}

.artifact-table {
  width: 100%;
}
</style>