<script setup lang="ts">
import { computed, ref } from 'vue'
import { useVirtualizer } from '@tanstack/vue-virtual'
import {
  productionStepLabel,
  type ProductionRuntimeLog,
} from '../../entities/production/production'
import LLMLogViewer from '../LLMLogViewer.vue'

const props = defineProps<{ logs: ProductionRuntimeLog[] }>()
const level = ref<'all' | 'error' | 'warning' | 'info'>('all')
const scrollElement = ref<HTMLElement | null>(null)
const filtered = computed(() =>
  [...props.logs]
    .reverse()
    .filter((row) => {
      if (level.value === 'all') return true
      if (level.value === 'warning') return ['warning', 'warn'].includes(row.level)
      return row.level === level.value
    }),
)
const virtualizer = useVirtualizer(
  computed(() => ({
    count: filtered.value.length,
    getScrollElement: () => scrollElement.value,
    estimateSize: () => 36,
    overscan: 12,
    getItemKey: (index: number) => filtered.value[index]?.id ?? index,
  })),
)
const rows = computed(() => virtualizer.value.getVirtualItems())
const totalHeight = computed(() => virtualizer.value.getTotalSize())
</script>

<template>
  <section class="production-logs">
    <article class="runtime-panel">
      <header>
        <div><strong>Agent 实时日志</strong><small>{{ filtered.length }} 条</small></div>
        <el-segmented
          v-model="level"
          :options="[
            { label: '全部', value: 'all' },
            { label: '错误', value: 'error' },
            { label: '警告', value: 'warning' },
            { label: '信息', value: 'info' },
          ]"
          aria-label="筛选实时日志"
        />
      </header>
      <div ref="scrollElement" class="log-scroll">
        <div v-if="filtered.length" class="virtual-list" :style="{ height: `${totalHeight}px` }">
          <div
            v-for="row in rows"
            :key="String(row.key)"
            class="log-row"
            :class="filtered[row.index]!.level"
            :style="{ transform: `translateY(${row.start}px)`, height: `${row.size}px` }"
          >
            <time>{{ new Date(filtered[row.index]!.timestamp * 1000).toLocaleTimeString() }}</time>
            <strong>{{ productionStepLabel(filtered[row.index]!.step) }}</strong>
            <span>{{ filtered[row.index]!.message }}</span>
          </div>
        </div>
        <el-empty v-else description="暂无当前项目的实时日志" :image-size="64" />
      </div>
    </article>
    <LLMLogViewer class="llm-panel" />
  </section>
</template>

<style scoped>
.production-logs { display: grid; grid-template-columns: minmax(0, 1fr) minmax(360px, 42%); gap: 12px; height: 100%; min-height: 0; padding: 12px; }
.runtime-panel { display: flex; min-width: 0; min-height: 0; flex-direction: column; overflow: hidden; border: 1px solid var(--color-border); border-radius: var(--radius-lg); background: var(--color-bg-surface); }
.runtime-panel > header { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 11px 13px; border-bottom: 1px solid var(--color-border); }
.runtime-panel > header > div { display: grid; gap: 2px; }
.runtime-panel strong { color: var(--color-text-strong); font-size: 12px; }
.runtime-panel small { color: var(--color-text-muted); font-size: 9px; }
.log-scroll { position: relative; flex: 1; min-height: 0; overflow: auto; padding: 6px 8px; }
.virtual-list { position: relative; width: 100%; }
.log-row { position: absolute; inset-inline: 0; top: 0; display: grid; grid-template-columns: 70px 100px minmax(0, 1fr); align-items: center; gap: 8px; padding: 0 8px; border-left: 3px solid transparent; color: var(--color-text); font-size: 10px; }
.log-row.error { border-left-color: var(--color-danger); background: var(--color-alert-danger-bg); }
.log-row.warning, .log-row.warn { border-left-color: var(--color-warning); }
.log-row time { color: var(--color-text-subtle); }
.log-row strong { overflow: hidden; color: var(--color-text-muted); font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.log-row span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.llm-panel { min-width: 0; min-height: 0; height: 100%; }
:deep(.llm-panel .el-card) { height: 100%; }
@media (max-width: 900px) { .production-logs { grid-template-columns: 1fr; grid-template-rows: minmax(260px, 1fr) minmax(260px, 1fr); } }
</style>
