<script setup lang="ts">
import { computed } from 'vue'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import { VueFlow, type Edge, type Node } from '@vue-flow/core'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'
import type { PlanningEntity, PlanningRelation } from '../../entities/planning/planningWorkspace'

const props = defineProps<{
  mode: 'cards' | 'relations' | 'timeline'
  entities: PlanningEntity[]
  relations: PlanningRelation[]
  timeline: Record<string, unknown>[]
}>()
const emit = defineEmits<{ select: [id: string] }>()

const graph = computed(() => {
  const rows = props.mode === 'relations'
    ? props.entities.filter((entity) => entity.kind === 'character')
    : props.mode === 'timeline'
      ? props.timeline.map((event, index) => ({
          id: String(event.id || `event-${index}`),
          name: String(event.summary || event.title || `事件 ${index + 1}`),
          kind: 'event',
        } as PlanningEntity))
      : props.entities.filter((entity) => entity.kind === 'outline')

  const nodes: Node[] = rows.map((entity, index) => ({
    id: entity.id,
    position: props.mode === 'timeline'
      ? { x: index * 230, y: index % 2 ? 150 : 40 }
      : { x: (index % 3) * 240, y: Math.floor(index / 3) * 150 },
    data: { label: entity.name },
    class: `planning-node planning-node--${entity.kind}`,
  }))
  const idsByName = new Map(rows.map((entity) => [entity.name, entity.id]))
  let edges: Edge[] = []
  if (props.mode === 'relations') {
    edges = props.relations
      .map((relation) => ({
        id: relation.id,
        source: idsByName.get(relation.source) || relation.source,
        target: idsByName.get(relation.target) || relation.target,
        label: relation.label,
        animated: Math.abs(relation.intensity) >= 0.7,
      }))
      .filter((edge) => nodes.some((node) => node.id === edge.source) && nodes.some((node) => node.id === edge.target))
  } else {
    edges = nodes.slice(1).map((node, index) => ({
      id: `sequence-${index}`,
      source: nodes[index].id,
      target: node.id,
    }))
  }
  return { nodes, edges }
})

function onNodeClick(payload: { node: Node }) {
  emit('select', payload.node.id)
}
</script>

<template>
  <div class="planning-canvas">
    <VueFlow
      v-if="graph.nodes.length"
      :nodes="graph.nodes"
      :edges="graph.edges"
      fit-view-on-init
      :min-zoom="0.3"
      :max-zoom="1.8"
      @node-click="onNodeClick"
    >
      <Background pattern-color="var(--color-border)" :gap="20" />
      <MiniMap pannable zoomable />
      <Controls position="bottom-right" />
    </VueFlow>
    <div v-else class="canvas-empty">
      <strong>当前视图还没有内容</strong>
      <p>从左侧选择实体，或在“编辑大纲”中补充策划信息。</p>
    </div>
  </div>
</template>

<style scoped>
.planning-canvas { width: 100%; height: 100%; min-height: 520px; background: var(--color-bg-canvas); }
:deep(.vue-flow) { min-height: 520px; }
.canvas-empty { height: 100%; display: grid; place-content: center; gap: 5px; color: var(--color-text-muted); text-align: center; }
.canvas-empty strong { color: var(--color-text-strong); }
.canvas-empty p { margin: 0; font-size: 12px; }
:deep(.planning-node) {
  min-width: 170px;
  padding: 12px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-surface);
  color: var(--color-text-strong);
  box-shadow: var(--shadow-sm);
}
:deep(.vue-flow__node.selected) { border-color: var(--color-primary); box-shadow: var(--shadow-focus); }
</style>
