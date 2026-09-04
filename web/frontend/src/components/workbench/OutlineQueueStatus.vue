<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getOutlineQueueStatus } from '../../api'

const loading = ref(false)
const status = ref<Record<string, any> | null>(null)

const load = async () => {
  loading.value = true
  try {
    const { data } = await getOutlineQueueStatus()
    status.value = data
  } catch {
    status.value = null
  } finally {
    loading.value = false
  }
}

onMounted(load)

defineExpose({ reload: load })
</script>

<template>
  <details v-if="status" class="queue-status panel" :open="true" v-loading="loading">
    <summary class="head" tabindex="0" role="button" aria-label="切换卷队列与拆章进度折叠状态">
      <div class="summary-title">
        <span class="chevron">▶</span>
        <h3>卷队列与拆章进度</h3>
      </div>
      <el-button size="small" link type="primary" @click.stop="load">刷新</el-button>
    </summary>
    <div class="details-content">
      <ul class="stats">
        <li>
          <span class="label">已写至</span>
          <strong>第 {{ status.last_written_chapter || 0 }} 章</strong>
        </li>
        <li>
          <span class="label">队列待发</span>
          <strong>{{ status.pending_briefs ?? 0 }} 章 brief</strong>
        </li>
        <li>
          <span class="label">规划窗口</span>
          <strong>{{ status.planning_window ?? '—' }} 章</strong>
        </li>
        <li v-if="status.current_macro_arc?.arc_id">
          <span class="label">当前宏观卷</span>
          <strong>{{ status.current_macro_arc.name || status.current_macro_arc.arc_id }}</strong>
          <span class="muted">（{{ status.current_macro_arc.chapters }}）</span>
        </li>
      </ul>
      <div v-if="(status.brief_ranges || []).length" class="ranges">
        <div v-for="r in status.brief_ranges" :key="r.arc_id" class="range-row">
          <span class="arc-id">{{ r.arc_id }}</span>
          <span>{{ r.arc_name }}</span>
          <span class="muted">
            brief {{ r.brief_count }} 章
            <template v-if="r.chapter_min != null"> · {{ r.chapter_min }}–{{ r.chapter_max }}</template>
          </span>
        </div>
      </div>
      <p v-if="status.arc_queue_stale?.stale" class="stale-hint">
        {{ status.arc_queue_stale.message || '卷队列可能与最新大纲不一致' }}
      </p>
      <p v-if="status.outline_layer_impl" class="layer-hint">
        层级：L0 设定 → macro 卷纲 → arc 章 brief（L1/L2 合并在卷纲，无单独文件）
      </p>
    </div>
  </details>
</template>

<style scoped>
.queue-status {
  padding: 12px 14px;
  margin-bottom: 12px;
  border: 1px solid #e4eaf2;
  border-radius: 8px;
  background: var(--color-bg-surface-muted);
}
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  list-style: none;
  user-select: none;
}
.head::-webkit-details-marker {
  display: none;
}
.summary-title {
  display: flex;
  align-items: center;
  gap: 8px;
}
.chevron {
  font-size: 10px;
  color: var(--color-text-muted);
  transition: transform 0.2s ease;
  display: inline-block;
}
details[open] .chevron {
  transform: rotate(90deg);
}
.details-content {
  margin-top: 10px;
}
.head h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: var(--color-text-strong);
}
.stats {
  list-style: none;
  margin: 0 0 8px;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 12px 20px;
  font-size: 13px;
}
.label {
  color: var(--color-text-muted);
  margin-right: 4px;
}
.muted {
  color: var(--color-text-subtle);
  font-size: 12px;
}
.ranges {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  max-height: 180px;
  overflow-y: auto;
  word-break: break-word;
  white-space: normal;
}
.range-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: baseline;
}
.arc-id {
  font-family: ui-monospace, monospace;
  color: var(--color-text-muted);
}
.stale-hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: #b45309;
}
.layer-hint {
  margin: 6px 0 0;
  font-size: 11px;
  color: var(--color-text-subtle);
}
</style>