<script setup lang="ts">
import type { OutlineQueueStatus } from '../../entities/outline/outlineQueueStatus'

defineProps<{ status: OutlineQueueStatus | null }>()
</script>

<template>
  <div v-if="status" class="queue-details">
    <ul class="stats">
      <li><span>已写至</span><strong>第 {{ status.last_written_chapter || 0 }} 章</strong></li>
      <li><span>队列待发</span><strong>{{ status.pending_briefs ?? 0 }} 章 brief</strong></li>
      <li><span>规划窗口</span><strong>{{ status.planning_window ?? '—' }} 章</strong></li>
      <li v-if="status.current_macro_arc?.arc_id"><span>当前宏观卷</span><strong>{{ status.current_macro_arc.name || status.current_macro_arc.arc_id }}</strong><em>（{{ status.current_macro_arc.chapters }}）</em></li>
    </ul>
    <div v-if="(status.brief_ranges || []).length" class="ranges">
      <div v-for="(range, index) in status.brief_ranges" :key="`${range.arc_id || range.arc_name || 'range'}-${index}`" class="range-row">
        <span class="arc-id">{{ range.arc_id || '—' }}</span>
        <span>{{ range.arc_name || '未命名阶段' }}</span>
        <span class="muted">brief {{ range.brief_count }} 章<template v-if="range.chapter_min != null"> · {{ range.chapter_min }}–{{ range.chapter_max }}</template></span>
      </div>
    </div>
    <p v-if="status.arc_queue_stale?.stale" class="stale-hint">{{ status.arc_queue_stale.message || '卷队列可能与最新大纲不一致，请回到策划页同步。' }}</p>
    <p v-if="status.outline_layer_impl" class="layer-hint">层级：L0 设定 → macro 卷纲 → arc 章 brief</p>
  </div>
  <el-empty v-else description="卷队列暂不可用" :image-size="64" />
</template>

<style scoped>
.stats { display: flex; flex-wrap: wrap; gap: 12px 20px; margin: 0 0 14px; padding: 0; list-style: none; font-size: 13px; }
.stats li { display: grid; gap: 2px; }
.stats span, .muted, .layer-hint { color: var(--color-text-muted); }
.stats strong { color: var(--color-text-strong); }
.stats em { color: var(--color-text-subtle); font-size: 11px; font-style: normal; }
.ranges { display: grid; gap: 7px; max-height: 260px; overflow-y: auto; padding-top: 12px; border-top: 1px solid var(--color-border-subtle); font-size: 12px; }
.range-row { display: flex; flex-wrap: wrap; align-items: baseline; gap: 7px; }
.arc-id { color: var(--color-text-muted); font-family: ui-monospace, monospace; }
.muted { font-size: 11px; }
.stale-hint { margin: 12px 0 0; color: var(--color-warning); font-size: 12px; }
.layer-hint { margin: 8px 0 0; font-size: 11px; }
</style>
