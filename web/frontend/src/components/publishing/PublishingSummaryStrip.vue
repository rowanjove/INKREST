<script setup lang="ts">
import { Check, Document, Files, Warning } from '@element-plus/icons-vue'

import type { PublishingWorkspace } from '../../entities/publishing/publishing'
import { formatWordCount } from '../../entities/publishing/publishing'

defineProps<{ workspace: PublishingWorkspace }>()
</script>

<template>
  <section class="summary-strip" aria-label="发布摘要">
    <article>
      <el-icon><Files /></el-icon>
      <div><strong>{{ workspace.book.chapter_count }}</strong><span>有效章节</span></div>
    </article>
    <article>
      <el-icon><Document /></el-icon>
      <div><strong>{{ formatWordCount(workspace.book.word_count) }}</strong><span>成书字数</span></div>
    </article>
    <article>
      <el-icon><Check /></el-icon>
      <div>
        <strong>{{ workspace.golden_check.ready_count }}/3</strong>
        <span>黄金章节</span>
      </div>
    </article>
    <article :class="{ warning: workspace.preflight.warning_count, danger: workspace.preflight.blocking_count }">
      <el-icon><Warning /></el-icon>
      <div>
        <strong>
          {{
            workspace.preflight.blocking_count
              ? `${workspace.preflight.blocking_count} 阻断`
              : workspace.preflight.warning_count
                ? `${workspace.preflight.warning_count} 提示`
                : '已就绪'
          }}
        </strong>
        <span>发布预检</span>
      </div>
    </article>
  </section>
</template>

<style scoped>
.summary-strip {
  display: grid;
  flex-shrink: 0;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}
.summary-strip article {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  background: var(--color-bg-surface);
  box-shadow: var(--shadow-sm);
}
.summary-strip .el-icon {
  width: 28px;
  height: 28px;
  flex: 0 0 28px;
  border-radius: 8px;
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.summary-strip article.warning .el-icon {
  background: var(--color-warning-soft);
  color: var(--color-warning);
}
.summary-strip article.danger .el-icon {
  background: var(--color-danger-soft);
  color: var(--color-danger);
}
.summary-strip article > div { display: grid; min-width: 0; gap: 1px; }
.summary-strip strong { color: var(--color-text-strong); font-size: 15px; line-height: 1.2; }
.summary-strip span { color: var(--color-text-muted); font-size: 9px; }
@media (max-width: 900px) {
  .summary-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
