<script setup lang="ts">
import { computed } from 'vue'
import StatusBadge from '../../shared/ui/StatusBadge.vue'
import { PLANNING_KIND_LABELS, type PlanningEntity } from '../../entities/planning/planningWorkspace'

const props = defineProps<{ entity: PlanningEntity | null }>()

const configuredRows = computed(() => Object.entries(props.entity?.configured || {}))
const currentRows = computed(() => Object.entries(props.entity?.current_state || {}))

function display(value: unknown): string {
  if (Array.isArray(value)) return value.join('、') || '—'
  if (value && typeof value === 'object') return JSON.stringify(value, null, 2)
  return String(value ?? '—') || '—'
}
</script>

<template>
  <aside class="inspector">
    <template v-if="entity">
      <header>
        <StatusBadge :label="PLANNING_KIND_LABELS[entity.kind] || entity.kind" tone="info" />
        <h2>{{ entity.name }}</h2>
        <p v-if="entity.summary">{{ entity.summary }}</p>
      </header>

      <section>
        <h3>设定</h3>
        <dl v-if="configuredRows.length">
          <div v-for="[key, value] in configuredRows" :key="key">
            <dt>{{ key }}</dt>
            <dd>{{ display(value) }}</dd>
          </div>
        </dl>
        <p v-else class="empty-copy">暂无配置设定</p>
      </section>

      <section>
        <h3>当前状态</h3>
        <dl v-if="currentRows.length">
          <div v-for="[key, value] in currentRows" :key="key">
            <dt>{{ key }}</dt>
            <dd>{{ display(value) }}</dd>
          </div>
        </dl>
        <p v-else class="empty-copy">正文尚未产生实际剧情状态</p>
      </section>

      <section>
        <h3>相关章节</h3>
        <div v-if="entity.related_chapters.length" class="chapter-tags">
          <el-tag v-for="chapter in entity.related_chapters" :key="chapter" size="small">{{ chapter }}</el-tag>
        </div>
        <p v-else class="empty-copy">暂无章节关联</p>
      </section>
    </template>
    <p v-else class="inspector-empty">从左侧或画布选择一个实体查看详情</p>
  </aside>
</template>

<style scoped>
.inspector { height: 100%; overflow: auto; padding: var(--space-4); background: var(--color-bg-surface); }
.inspector header { padding-bottom: var(--space-4); border-bottom: 1px solid var(--color-border-subtle); }
.inspector h2 { margin: 8px 0 4px; color: var(--color-text-strong); font-size: 18px; }
.inspector header p { margin: 0; color: var(--color-text-muted); font-size: 12px; line-height: 1.6; }
.inspector section { margin-top: var(--space-5); }
.inspector h3 { margin: 0 0 8px; color: var(--color-text-strong); font-size: 13px; }
.inspector dl { display: grid; gap: 8px; margin: 0; }
.inspector dl div { display: grid; gap: 2px; padding-bottom: 8px; border-bottom: 1px solid var(--color-border-subtle); }
.inspector dt { color: var(--color-text-muted); font-size: 11px; }
.inspector dd { margin: 0; color: var(--color-text); font-size: 12px; line-height: 1.55; white-space: pre-wrap; word-break: break-word; }
.empty-copy,
.inspector-empty { color: var(--color-text-muted); font-size: 12px; line-height: 1.6; }
.inspector-empty { margin-top: 40px; text-align: center; }
.chapter-tags { display: flex; flex-wrap: wrap; gap: 6px; }
</style>
