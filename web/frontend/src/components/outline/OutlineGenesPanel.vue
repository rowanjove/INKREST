<script setup lang="ts">
import { Brush, Edit } from '@element-plus/icons-vue'

defineProps<{
  genreGenes: Record<string, any>
  onOpenEditGenes: () => void
}>()
</script>

<template>
  <div class="config-strip config-strip-single">
    <section class="config-card genes-panel">
      <div class="config-card-head">
        <div class="config-card-title">
          <el-icon class="panel-icon genes-color"><Brush /></el-icon>
          <h2>类型基因</h2>
        </div>
        <el-button text type="primary" :icon="Edit" size="small" @click="onOpenEditGenes">编辑</el-button>
      </div>
      <dl class="config-kv">
        <div>
          <dt>爽点机制</dt>
          <dd class="ellipsis">{{ genreGenes?.pleasure_mechanism || '未设定' }}</dd>
        </div>
        <div>
          <dt>主角弧线</dt>
          <dd class="ellipsis">{{ genreGenes?.protagonist_arc || '未设定' }}</dd>
        </div>
        <div>
          <dt>感情线</dt>
          <dd class="ellipsis">{{ genreGenes?.romance_weight || '未设定' }}</dd>
        </div>
        <div>
          <dt>节奏基调</dt>
          <dd class="ellipsis">{{ genreGenes?.pacing_baseline || '未设定' }}</dd>
        </div>
      </dl>
      <div v-if="genreGenes?.drift_guards?.length" class="guard-inline">
        <span class="guard-label">防跑偏</span>
        <el-tag v-for="guard in genreGenes.drift_guards" :key="guard" size="small" type="info">{{ guard }}</el-tag>
      </div>
    </section>
  </div>
</template>

<style scoped>
.config-strip {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  flex-shrink: 0;
}

.config-strip-single {
  grid-template-columns: minmax(0, 1fr);
}

.config-card {
  border: 1px solid #e1e7ef;
  border-radius: 8px;
  background: var(--color-bg-surface);
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 0;
}

.config-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.config-card-title {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.config-card-title h2 {
  margin: 0;
  font-size: 15px;
  font-weight: 800;
  color: #111827;
}

.panel-icon.genes-color {
  color: #67c23a;
  font-size: 16px;
}

.config-kv {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px 10px;
  margin: 0;
}

.config-kv dt {
  margin: 0;
  font-size: 12px;
  color: var(--color-text-subtle);
  font-weight: 600;
}

.config-kv dd {
  margin: 2px 0 0;
  font-size: 13.5px;
  font-weight: 700;
  color: var(--color-text-strong);
}

.ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.guard-inline {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.guard-label {
  font-size: 11px;
  color: var(--color-text-subtle);
  flex-shrink: 0;
}

@media (max-width: 1280px) {
  .config-kv {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>