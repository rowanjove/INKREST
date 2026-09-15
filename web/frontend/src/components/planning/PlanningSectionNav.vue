<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

type PlanningSection = 'outline' | 'atlas' | 'assets' | 'state'

const route = useRoute()
const router = useRouter()

const activeSection = computed<PlanningSection>(() => {
  if (route.path === '/assets') return 'assets'
  if (route.path === '/state') return 'state'
  return ['mindmap', 'cards', 'relations', 'timeline'].includes(String(route.query.view || ''))
    ? 'atlas'
    : 'outline'
})

const sections: Array<{ id: PlanningSection; label: string; hint: string; location: string | { path: string; query: Record<string, string> } }> = [
  { id: 'outline', label: '大纲编辑', hint: '书名、题材、卷纲与生成约束', location: '/outline' },
  { id: 'atlas', label: '故事图谱', hint: '思维导图、实体、关系与时间线', location: { path: '/outline', query: { view: 'mindmap' } } },
  { id: 'assets', label: '素材资产', hint: '人物、世界、规则与自定义素材', location: '/assets' },
  { id: 'state', label: '剧情状态', hint: '伏笔、物品、事件与编年史', location: '/state' },
]
</script>

<template>
  <nav class="planning-section-nav" aria-label="策划工作区">
    <button
      v-for="section in sections"
      :key="section.id"
      type="button"
      :class="{ active: activeSection === section.id }"
      :aria-current="activeSection === section.id ? 'page' : undefined"
      @click="router.push(section.location)"
    >
      <strong>{{ section.label }}</strong>
      <small>{{ section.hint }}</small>
    </button>
  </nav>
</template>

<style scoped>
.planning-section-nav {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px;
  padding: 8px var(--space-5);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-surface);
}
.planning-section-nav button {
  min-width: 0;
  display: grid;
  gap: 3px;
  padding: 9px 12px;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  text-align: left;
}
.planning-section-nav button:hover { background: var(--color-bg-hover); color: var(--color-text-strong); }
.planning-section-nav button.active {
  border-color: color-mix(in srgb, var(--color-primary) 34%, var(--color-border));
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.planning-section-nav strong { overflow: hidden; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.planning-section-nav small { overflow: hidden; font-size: 10.5px; font-weight: 500; text-overflow: ellipsis; white-space: nowrap; }
@media (max-width: 920px) {
  .planning-section-nav { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
