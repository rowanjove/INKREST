<script setup lang="ts">
import { Warning } from '@element-plus/icons-vue'

defineProps<{
  diff: {
    old_chapters: any[]
    new_chapters: any[]
  }
  applying: boolean
}>()

const visible = defineModel<boolean>({ required: true })

const emit = defineEmits<{
  apply: []
}>()
</script>

<template>
  <el-dialog v-model="visible" title="大纲自适应纠偏对比" width="850px" top="8vh" destroy-on-close>
    <div class="outline-diff-container">
      <div class="diff-header-info">
        <el-icon class="warning-icon"><Warning /></el-icon>
        <div>
          <h4>主编整改指令已生成</h4>
          <p>已针对当前异常跳出率对后续 3 章大纲进行重写，压缩日常并提升核心戏剧冲突。请对比并决定是否应用：</p>
        </div>
      </div>

      <div class="diff-columns">
        <div class="diff-col old-chapters-col">
          <h3>原定大纲走向</h3>
          <div class="diff-chapters-scroll">
            <div v-for="ch in diff.old_chapters" :key="ch.chapter_id" class="diff-chapter-card">
              <div class="ch-title">第 {{ ch.chapter_id }} 章：{{ ch.title || ch.chapter_title }}</div>
              <div class="ch-content">{{ ch.goal || ch.detailed_synopsis }}</div>
            </div>
          </div>
        </div>

        <div class="diff-col new-chapters-col">
          <h3>纠偏后走向（加速爽点爆发）</h3>
          <div class="diff-chapters-scroll">
            <div v-for="ch in diff.new_chapters" :key="ch.chapter_id" class="diff-chapter-card highlight-card">
              <div class="ch-title">第 {{ ch.chapter_id }} 章：{{ ch.chapter_title || ch.title }}</div>
              <div class="ch-content">{{ ch.detailed_synopsis || ch.goal }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="danger" :loading="applying" @click="emit('apply')">确认应用纠偏大纲</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.outline-diff-container {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.diff-header-info {
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
  padding: 12px 16px;
  display: flex;
  gap: 12px;
  align-items: center;
}

.warning-icon {
  font-size: 26px;
  color: var(--color-warning);
}

.diff-header-info h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 800;
  color: #92400e;
}

.diff-header-info p {
  margin: 2px 0 0;
  font-size: 12.5px;
  color: #b45309;
}

.diff-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.diff-col {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
  background: var(--color-bg-surface);
}

.diff-col h3 {
  margin: 0;
  background: var(--color-bg-surface-muted);
  padding: 10px 14px;
  font-size: 13.5px;
  font-weight: 800;
  color: var(--color-text);
  border-bottom: 1px solid var(--color-border);
}

.diff-chapters-scroll {
  height: 380px;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: var(--color-bg-surface-muted);
}

.diff-chapter-card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 10px;
  font-size: 12.5px;
}

.diff-chapter-card .ch-title {
  font-weight: 800;
  color: var(--color-text-strong);
  margin-bottom: 4px;
}

.diff-chapter-card .ch-content {
  color: var(--color-text-muted);
  line-height: 1.4;
}

.highlight-card {
  border-color: #bbf7d0;
  background: #f0fdf4;
}

.highlight-card .ch-title {
  color: #15803d;
}

.highlight-card .ch-content {
  color: #166534;
}
</style>