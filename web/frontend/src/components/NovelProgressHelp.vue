<script setup lang="ts">
import { computed } from 'vue'
import { useNovelProgress } from '../composables/useNovelProgress'
import { EXTERNAL_AUDIT_HINT, INTERNAL_GATE_HINT } from '../constants/repairWorkflow'

const { snapshot, loading, refresh } = useNovelProgress({ pollMs: 12000 })

const progress = computed(() => snapshot.value)
</script>

<template>
  <details class="progress-help panel">
    <summary>
      <span>进度数字怎么理解？</span>
      <el-tag v-if="(progress?.pending_total ?? 0) > 0" type="danger" size="small" effect="plain">
        待处理 {{ progress?.pending_total }}
      </el-tag>
      <el-tag v-if="progress?.batch_paused" type="warning" size="small" effect="plain">批量已暂停</el-tag>
      <el-button link type="primary" size="small" :loading="loading" @click.stop="refresh">
        刷新
      </el-button>
    </summary>
    <div class="body">
      <ul class="metric-list">
        <li>
          <strong>书库 / SQLite 章数</strong>
          <span>{{ progress?.library_indexed ?? '—' }} 章</span>
          — 索引口径（含手动新建）。
        </li>
        <li>
          <strong>磁盘有正文章数</strong>
          <span>{{ progress?.disk_chapters_with_final ?? '—' }} 章</span>
          — 存在 chapter_final.txt 的目录数，可能与批量计数不同步。
        </li>
        <li class="metric-primary">
          <strong>全书批量进度（权威）</strong>
          <span>{{ progress?.authoritative_completed ?? '—' }} 章已完成</span>
          — 续跑与熔断以 <code>novel_batch_progress</code> 为准，勿仅看书库章数。
        </li>
        <li v-if="(progress?.pending_total ?? 0) > 0">
          <strong>待处理章节</strong>
          <span>{{ progress?.pending_total }} 项</span>
          （门禁 {{ progress?.pending_gate_count }} · 批量跳过 {{ progress?.pending_retry_count }}）— 修完再「继续写书」。
        </li>
        <li v-if="progress && progress.remaining_chapters > 0">
          <strong>开书清单剩余额度</strong>
          <span>还可连写约 {{ progress.remaining_chapters }} 章</span>
          — 大纲上限减去已落库章数。
        </li>
        <li v-if="progress?.last_chapter_id">
          <strong>最近批量断点</strong>
          <span>卷 {{ progress.last_arc_id || '—' }} / 章 {{ progress.last_chapter_id }}</span>
          — 暂停或熔断时的最后处理章。
        </li>
        <li>
          <strong>工作台生产线步骤条</strong>
          — 当前正在跑的单章流水线实时步骤，与全书批量进度独立。
        </li>
      </ul>
      <p class="footnote">
        若三处数字不一致，以章节维护「待处理」+ 批量断点为准排查；连写续跑请用「继续写书」弹窗，勿裸调 API。
        {{ INTERNAL_GATE_HINT }}
        {{ EXTERNAL_AUDIT_HINT }}
      </p>
    </div>
  </details>
</template>

<style scoped>
.progress-help {
  margin-bottom: 12px;
  padding: 10px 14px;
  border-radius: 10px;
  border: 1px solid var(--color-border, #e4e7ed);
  background: var(--color-bg-surface, #fff);
}

.progress-help summary {
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text, #303133);
  display: flex;
  align-items: center;
  gap: 8px;
  list-style: none;
}

.progress-help summary::-webkit-details-marker {
  display: none;
}

.body {
  margin-top: 10px;
}

.metric-list {
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 12.5px;
  line-height: 1.65;
  color: var(--color-text-muted, #606266);
}

.metric-list li {
  margin-bottom: 6px;
}

.metric-list strong {
  color: var(--color-text, #303133);
  margin-right: 4px;
}

.metric-list code {
  font-size: 11px;
}

.footnote {
  margin: 10px 0 0;
  font-size: 12px;
  color: var(--color-text-muted, #909399);
}
</style>