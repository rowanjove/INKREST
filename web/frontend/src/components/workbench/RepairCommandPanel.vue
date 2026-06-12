<script setup lang="ts">
import { Tools } from '@element-plus/icons-vue'
import type { FactoryRepairSummary } from '../../types/factory'

defineProps<{
  repair: FactoryRepairSummary | null | undefined
}>()

const emit = defineEmits<{
  repair: [chapterId: string]
  edit: [chapterId: string]
  rerunGate: [chapterId: string]
}>()
</script>

<template>
  <section class="repair-command-panel">
    <div class="panel-title">
      <el-icon><Tools /></el-icon>
      <h3>自动修复中心</h3>
      <el-tag v-if="repair?.blocked_count" type="danger" effect="plain">
        {{ repair.blocked_count }} 章待处理
      </el-tag>
    </div>

    <p v-if="!repair?.items.length" class="empty-copy">
      暂无阻断章节。生产线可以继续向前推进。
    </p>

    <div v-else class="repair-list">
      <article v-for="item in repair.items" :key="item.chapter_id" class="repair-item">
        <div class="repair-copy">
          <strong>{{ item.title }}</strong>
          <span>{{ item.reason }}</span>
          <p>{{ item.manual_hint }}</p>
        </div>
        <div class="repair-actions">
          <el-button
            size="small"
            type="primary"
            :disabled="item.recommended_action !== 'auto_repair'"
            @click="emit('repair', item.chapter_id)"
          >
            自动修复
          </el-button>
          <el-button size="small" plain @click="emit('edit', item.chapter_id)">去改稿</el-button>
          <el-button
            size="small"
            plain
            :disabled="item.recommended_action === 'manual_edit'"
            @click="emit('rerunGate', item.chapter_id)"
          >
            只重跑门禁
          </el-button>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.repair-command-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-surface);
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

h3 {
  margin: 0;
  font-size: 16px;
}

.empty-copy {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 13px;
}

.repair-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.repair-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  padding: 10px;
  border-radius: 8px;
  background: var(--color-bg-surface-muted);
}

.repair-copy {
  min-width: 0;
}

.repair-copy strong,
.repair-copy span {
  display: block;
}

.repair-copy span,
.repair-copy p {
  color: var(--color-text-muted);
  font-size: 12px;
}

.repair-copy p {
  margin: 4px 0 0;
}

.repair-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

@media (max-width: 900px) {
  .repair-item {
    grid-template-columns: 1fr;
  }

  .repair-actions {
    justify-content: flex-start;
  }
}
</style>
