<script setup lang="ts">
import { computed } from 'vue'
import { PLANNING_KIND_LABELS, type PlanningEntity } from '../../entities/planning/planningWorkspace'

const props = defineProps<{
  entities: PlanningEntity[]
  selectedId: string
}>()

const query = defineModel<string>('query', { required: true })
const emit = defineEmits<{ select: [entity: PlanningEntity] }>()

const groups = computed(() => {
  const grouped = new Map<string, PlanningEntity[]>()
  for (const entity of props.entities) {
    const rows = grouped.get(entity.kind) || []
    rows.push(entity)
    grouped.set(entity.kind, rows)
  }
  return [...grouped.entries()]
})
</script>

<template>
  <aside class="entity-tree">
    <el-input v-model="query" clearable placeholder="搜索实体…" aria-label="搜索故事实体" />
    <div v-if="groups.length" class="entity-groups">
      <section v-for="[kind, items] in groups" :key="kind" class="entity-group">
        <h3>{{ PLANNING_KIND_LABELS[kind] || kind }} <span>{{ items.length }}</span></h3>
        <button
          v-for="entity in items"
          :key="entity.id"
          type="button"
          :class="{ active: selectedId === entity.id }"
          @click="emit('select', entity)"
        >
          <span>{{ entity.name }}</span>
          <small v-if="entity.summary">{{ entity.summary }}</small>
        </button>
      </section>
    </div>
    <p v-else class="tree-empty">暂无匹配实体</p>
  </aside>
</template>

<style scoped>
.entity-tree { height: 100%; overflow: auto; padding: var(--space-3); background: var(--color-bg-surface); }
.entity-groups { display: grid; gap: var(--space-4); margin-top: var(--space-4); }
.entity-group h3 {
  display: flex;
  justify-content: space-between;
  margin: 0 0 6px;
  color: var(--color-text-muted);
  font-size: 11px;
  letter-spacing: .08em;
  text-transform: uppercase;
}
.entity-group button {
  width: 100%;
  display: grid;
  gap: 2px;
  padding: 8px 10px;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text);
  text-align: left;
  cursor: pointer;
}
.entity-group button:hover,
.entity-group button.active { background: var(--color-bg-surface-muted); color: var(--color-primary); }
.entity-group small {
  overflow: hidden;
  color: var(--color-text-muted);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tree-empty { color: var(--color-text-muted); font-size: 12px; text-align: center; }
</style>
