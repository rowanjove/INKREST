<script setup lang="ts">
import type { ChapterProgress } from '../../entities/project/projectSnapshot'

defineProps<{ progress: ChapterProgress }>()
</script>

<template>
  <div class="details-body">
    <ul class="metric-list">
      <li><strong>书库 / SQLite 章数</strong><span>{{ progress.library_indexed ?? '—' }} 章</span> — 索引口径，含手动新建。</li>
      <li><strong>磁盘有正文章数</strong><span>{{ progress.disk_chapters_with_final ?? '—' }} 章</span> — 存在 `chapter_final.txt` 的目录数。</li>
      <li class="metric-primary"><strong>全书批量进度（权威）</strong><span>{{ progress.authoritative_completed ?? '—' }} 章已完成</span> — 续跑与熔断以批量进度为准。</li>
      <li v-if="Number(progress.pending_total || 0) > 0"><strong>待处理章节</strong><span>{{ progress.pending_total }} 项</span> — 门禁 {{ progress.pending_gate_count || 0 }} · 批量跳过 {{ progress.pending_retry_count || 0 }}。</li>
      <li v-if="Number(progress.remaining_chapters || 0) > 0"><strong>开书清单剩余额度</strong><span>还可连写约 {{ progress.remaining_chapters }} 章</span> — 大纲上限减去已落库章数。</li>
      <li v-if="progress.last_chapter_id"><strong>最近批量断点</strong><span>卷 {{ progress.last_arc_id || '—' }} / 章 {{ progress.last_chapter_id }}</span> — 暂停或熔断时的最后处理章。</li>
      <li><strong>工作台生产线步骤条</strong> — 当前单章流水线实时步骤，与全书批量进度独立。</li>
    </ul>
    <p class="footnote">若三处数字不一致，以生产中心“审校修复”与批量断点为准排查；连写续跑请使用确认弹窗。</p>
  </div>
</template>

<style scoped>
.details-body { min-height: 0; }
.metric-list { margin: 0; padding: 0; list-style: none; color: var(--color-text-muted); font-size: 12.5px; line-height: 1.65; }
.metric-list li { margin-bottom: 8px; }
.metric-list strong { margin-right: 5px; color: var(--color-text-strong); }
.metric-list span { margin-right: 4px; color: var(--color-text); font-weight: 650; }
.metric-primary { padding-left: 10px; border-left: 2px solid var(--color-primary); }
.footnote { margin: 12px 0 0; color: var(--color-text-subtle); font-size: 11px; line-height: 1.6; }
</style>

