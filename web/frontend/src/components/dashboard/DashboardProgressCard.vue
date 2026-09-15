<script setup lang="ts">
import { QuestionFilled } from '@element-plus/icons-vue'
import type { ChapterProgress } from '../../entities/project/projectSnapshot'
import { progressHasSourceMismatch, progressTone } from '../../utils/overviewProgress'

defineProps<{
  chapterProgress: ChapterProgress
  completed: number
  target: number
  percentage: number
  onOpenDetails: () => void
}>()
</script>

<template>
  <article class="summary-card progress-card" :class="`tone-${progressTone(chapterProgress)}`">
    <div class="card-heading">
      <span>正文进度</span>
      <button
        type="button"
        class="help-button"
        aria-label="查看进度口径"
        title="查看进度口径"
        @click="onOpenDetails"
      >
        <el-icon><QuestionFilled /></el-icon>
      </button>
    </div>
    <strong>{{ completed }}<small> / {{ target || '—' }} 章</small></strong>
    <el-progress :percentage="percentage" :show-text="false" />
    <p class="progress-meta">
      书库 {{ chapterProgress.library_indexed ?? '—' }} · 磁盘终稿 {{ chapterProgress.disk_chapters_with_final ?? '—' }} · 待处理 {{ chapterProgress.pending_total ?? 0 }}
      <span v-if="progressHasSourceMismatch(chapterProgress)" class="mismatch-dot" title="不同数据源的章数不一致" aria-label="不同数据源的章数不一致">!</span>
    </p>
  </article>
</template>

<style scoped>
.summary-card { min-width: 0; padding: var(--space-5); border: 1px solid var(--color-border); border-radius: var(--radius-lg); background: var(--color-bg-surface); box-shadow: var(--shadow-sm); }
.card-heading { display: flex; align-items: center; justify-content: space-between; gap: var(--space-2); color: var(--color-text-muted); font-size: 12px; }
.help-button { display: inline-grid; width: 24px; height: 24px; place-items: center; border: 0; border-radius: 50%; background: transparent; color: var(--color-text-subtle); cursor: pointer; }
.help-button:hover, .help-button:focus-visible { background: var(--color-primary-soft); color: var(--color-primary); outline: none; }
.summary-card > strong { display: block; margin: var(--space-4) 0 5px; color: var(--color-text-strong); font-size: 30px; }
.summary-card strong small { color: var(--color-text-muted); font-size: 13px; font-weight: 500; }
.progress-meta { margin: 8px 0 0; color: var(--color-text-muted); font-size: 11px; line-height: 1.5; overflow-wrap: anywhere; }
.mismatch-dot { display: inline-grid; width: 16px; height: 16px; margin-left: 4px; place-items: center; border-radius: 50%; background: var(--color-warning-soft); color: var(--color-warning); font-size: 10px; font-weight: 800; }
.tone-warning { border-color: color-mix(in srgb, var(--color-warning) 38%, var(--color-border)); }
.tone-danger { border-color: color-mix(in srgb, var(--color-danger) 38%, var(--color-border)); }
</style>
