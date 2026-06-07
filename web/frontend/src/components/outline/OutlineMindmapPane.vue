<script setup lang="ts">
import { Tickets } from '@element-plus/icons-vue'

defineProps<{
  title: string
  genre: string
  targetChapters: number
  arcs: any[]
  connections: Array<{ d: string }>
  setNodeRef: (id: string, el: Element | null) => void
  displayIndex: (index: string | number) => number
}>()
</script>

<template>
  <div class="mindmap-wrapper panel">
    <div class="mindmap-canvas">
      <svg class="canvas-svg">
        <path
          v-for="(link, i) in connections"
          :key="i"
          :d="link.d"
          fill="none"
          stroke="#ffcfbc"
          stroke-width="2.5"
        />
      </svg>

      <div class="mindmap-tree">
        <div class="tree-column center-col">
          <div
            :ref="el => setNodeRef('center-node', el as Element | null)"
            class="mm-node root-node"
          >
            <span class="node-tag">作品中心</span>
            <h3>{{ title }}</h3>
            <small>{{ genre }} · {{ targetChapters }} 章</small>
          </div>
        </div>

        <div class="tree-column branches-col">
          <div class="branch-group">
            <div
              :ref="el => setNodeRef('branch-arcs', el as Element | null)"
              class="mm-node branch-node arcs-branch"
            >
              <el-icon><Tickets /></el-icon>
              <strong>推进篇章 (Arcs)</strong>
            </div>
            <div class="leaf-nodes">
              <div
                v-for="(arc, idx) in arcs"
                :key="`arc-${idx}`"
                :ref="el => setNodeRef(`arc-node-${idx}`, el as Element | null)"
                class="mm-node leaf-node arc-node-item"
              >
                <span class="arc-badge">Phase {{ displayIndex(idx) }}</span>
                <strong>{{ arc.title || arc.name || `阶段 ${displayIndex(idx)}` }}</strong>
                <p>{{ arc.summary || arc.description || arc.goal || arc }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.mindmap-wrapper {
  flex: 1;
  min-height: 0;
  padding: 12px;
  overflow: auto;
  background: var(--color-bg-surface-muted);
  border: 1px solid #e1e7ef;
  border-radius: 8px;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04);
}

.mindmap-canvas {
  position: relative;
  min-width: 1100px;
  min-height: 520px;
  padding: 8px;
}

.canvas-svg {
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
}

.mindmap-tree {
  position: relative;
  display: flex;
  gap: 120px;
  z-index: 5;
  min-height: 480px;
}

.tree-column {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.center-col {
  width: 260px;
  flex-shrink: 0;
}

.branches-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 60px;
  justify-content: space-around;
}

.branch-group {
  display: flex;
  align-items: center;
  gap: 120px;
}

.mm-node {
  background: white;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 14px 18px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 4px;
  transition: all 0.2s ease;
}

.mm-node:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(198, 111, 79, 0.08);
  border-color: #ffbba1;
}

.root-node {
  border: 2px solid var(--primary);
  box-shadow: 0 10px 28px rgba(198, 111, 79, 0.1);
  padding: 20px;
}

.root-node h3 {
  margin: 4px 0;
  font-size: 20px;
  color: var(--color-text-strong);
}

.root-node small {
  color: var(--text-muted);
}

.node-tag {
  font-size: 10px;
  text-transform: uppercase;
  font-weight: 800;
  color: var(--primary);
  letter-spacing: 1px;
}

.branch-node {
  width: 180px;
  flex-direction: row !important;
  align-items: center;
  gap: 8px !important;
  font-size: 15px;
  color: var(--color-text-strong);
  border-left: 4px solid var(--color-text-subtle);
  flex-shrink: 0;
}

.arcs-branch {
  border-left-color: #8b5cf6;
}

.leaf-nodes {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 320px;
}

.leaf-node {
  border-radius: 6px;
  padding: 10px 14px;
}

.leaf-node p {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-muted);
  line-height: 1.5;
}

.leaf-node strong {
  font-size: 14px;
  color: var(--color-text-strong);
}

.arc-node-item {
  border-left: 3px solid #f3e8ff;
  background: #faf5ff;
  max-width: 440px;
}

.arc-node-item strong {
  color: #6b21a8;
  font-size: 14.5px;
  margin: 4px 0;
}

.arc-node-item p {
  color: #582787;
}

.arc-badge {
  font-size: 10px;
  font-weight: 800;
  color: #a855f7;
  text-transform: uppercase;
}
</style>