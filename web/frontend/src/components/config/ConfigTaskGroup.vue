<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { CONFIG_SECTION_ALIASES } from '../../utils/configSections'

const props = withDefaults(
  defineProps<{
    id: string
    eyebrow: string
    title: string
    description: string
    defaultExpanded?: boolean
  }>(),
  {
    defaultExpanded: true,
  },
)

const route = useRoute()
const expanded = ref(props.defaultExpanded)

const toggle = () => {
  expanded.value = !expanded.value
}

const checkHash = () => {
  const raw = (route.hash || '').replace(/^#/, '')
  const target = CONFIG_SECTION_ALIASES[raw] || raw
  if (target === props.id) {
    expanded.value = true
  }
}

onMounted(checkHash)
watch(() => route.hash, checkHash)

defineExpose({ expanded, toggle })
</script>

<template>
  <section :id="id" class="config-task-group fold-card" :class="{ 'is-expanded': expanded }">
    <header class="task-group-head fold-head" @click="toggle">
      <div class="head-left">
        <span class="collapse-arrow" :class="{ open: expanded }">▶</span>
        <span class="task-eyebrow">{{ eyebrow }}</span>
        <div class="title-wrap">
          <h2>{{ title }}</h2>
          <p>{{ description }}</p>
        </div>
      </div>
      <div v-if="$slots.extra" class="head-actions" @click.stop>
        <slot name="extra" />
      </div>
    </header>
    <div v-show="expanded" class="task-group-body fold-body">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.config-task-group {
  scroll-margin-top: 16px;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md, 10px);
  background: var(--color-bg-surface);
  box-shadow: var(--shadow-card);
}

.task-group-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 14px;
  cursor: pointer;
  user-select: none;
  transition: background var(--motion-fast) var(--ease-standard);
}

.task-group-head:hover {
  background: var(--color-bg-surface-muted);
}

.head-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1;
}

.collapse-arrow {
  color: var(--color-text-subtle);
  font-size: 12px;
  flex-shrink: 0;
  transition: transform 0.18s ease;
}

.collapse-arrow.open {
  transform: rotate(90deg);
}

.task-eyebrow {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 850;
  color: var(--color-primary);
  letter-spacing: .08em;
  text-transform: uppercase;
}

.title-wrap {
  min-width: 0;
}

.title-wrap h2 {
  margin: 0;
  color: var(--color-text-strong);
  font-size: 14px;
  font-weight: 750;
  line-height: 1.25;
}

.title-wrap p {
  margin: 2px 0 0;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.35;
}

.head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.task-group-body {
  display: grid;
  gap: 8px;
  padding: 10px 14px 12px;
  border-top: 1px solid var(--color-border-subtle);
  background: var(--color-bg-surface);
}

.task-group-body :deep(.bare-content) {
  display: grid;
  gap: 8px;
}

.task-group-body :deep(.is-bare) {
  border: none !important;
  box-shadow: none !important;
  background: transparent !important;
  border-radius: 0 !important;
  padding: 0 !important;
  margin: 0 !important;
}

.task-group-body :deep(.is-bare > .fold-body) {
  padding: 0 !important;
  border-top: none !important;
}

@media (max-width: 720px) {
  .task-group-head {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  .head-actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>
