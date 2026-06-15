<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowDown, CircleCheck, CircleClose, Warning } from '@element-plus/icons-vue'
import {
  buildReadinessItems,
  longFormVectorWarn,
  LONG_FORM_VECTOR_WARN_TEXT,
  readinessAllOk,
  readinessTrafficLight,
  type ReadinessItem,
  type VectorReadinessContext,
} from '../../utils/projectReadiness'

const props = defineProps<{
  engineReady: boolean
  outline: Record<string, unknown> | null
  assets: Array<{ name: string; size?: number }>
  maxAvailableChapters: number
  vectorReadiness: VectorReadinessContext
  workScale?: string
}>()

const router = useRouter()
const expanded = ref(false)

const items = computed<ReadinessItem[]>(() =>
  buildReadinessItems({
    engineReady: props.engineReady,
    outline: props.outline,
    assets: props.assets,
    maxAvailableChapters: props.maxAvailableChapters,
    ...props.vectorReadiness,
    workScale: props.workScale,
  }),
)

const allOk = computed(() => readinessAllOk(items.value))
const trafficLight = computed(() => readinessTrafficLight(items.value))

const pendingCount = computed(() => items.value.filter((i) => !i.ok).length)
const warnCount = computed(() => items.value.filter((i) => i.warn).length)
const progressTotal = computed(() => items.value.length)
const progressOk = computed(() => items.value.filter((i) => i.ok).length)
const progressPercent = computed(() => {
  const total = progressTotal.value
  if (!total) return 0
  return Math.round((progressOk.value / total) * 100)
})

const showVectorBanner = computed(() =>
  longFormVectorWarn({
    workScale: props.workScale || '',
    ...props.vectorReadiness,
  }),
)

const go = (route: string) => router.push(route)

const openEmbedding = () => router.push('/config')
</script>

<template>
  <section class="readiness-row panel">
    <button type="button" class="readiness-head" @click="expanded = !expanded">
      <span :class="['traffic-light', trafficLight]" aria-hidden="true" />
      <div class="head-copy">
        <h2>开书清单</h2>
        <p v-if="!expanded" class="readiness-desc">
          {{ allOk ? '全部就绪，可连写启动' : `${pendingCount} 项待完成` }}
          <template v-if="warnCount > 0 && allOk"> · {{ warnCount }} 项建议优化</template>
        </p>
        <div v-if="!expanded && progressTotal > 0" class="readiness-progress" aria-label="开书清单进度">
          <el-progress
            :percentage="progressPercent"
            :stroke-width="6"
            :show-text="false"
            :status="allOk ? 'success' : undefined"
          />
          <span class="readiness-progress-label">{{ progressOk }}/{{ progressTotal }} 项就绪</span>
        </div>
        <p v-else class="readiness-desc">全绿后在下方生产线点「连写启动」</p>
      </div>
      <span :class="['readiness-badge', allOk ? 'ok' : 'pending']">
        {{ allOk ? '可开跑' : '待完成' }}
      </span>
      <el-icon class="collapse-chevron" :class="{ open: expanded }"><ArrowDown /></el-icon>
    </button>
    <el-alert
      v-if="showVectorBanner"
      type="warning"
      :closable="false"
      show-icon
      class="vector-warn-banner"
      title="长篇向量未就绪"
    >
      <p>{{ LONG_FORM_VECTOR_WARN_TEXT }}</p>
      <el-button size="small" type="warning" plain @click.stop="openEmbedding">去配置 Embedding</el-button>
    </el-alert>
    <div v-show="expanded" class="readiness-cards">
      <button
        v-for="item in items"
        :key="item.id"
        type="button"
        class="readiness-chip"
        :class="{
          ok: item.ok && !item.warn,
          warn: item.warn,
          no: !item.ok && !item.warn,
        }"
        @click="go(item.route)"
      >
        <el-icon class="chip-icon">
          <Warning v-if="item.warn" />
          <CircleCheck v-else-if="item.ok" />
          <CircleClose v-else />
        </el-icon>
        <span class="chip-label">{{ item.label }}</span>
        <span v-if="item.hint && (item.warn || !item.ok)" class="chip-hint">{{ item.hint }}</span>
      </button>
    </div>
  </section>
</template>

<style scoped>
.readiness-row {
  padding: 0;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-bg-surface);
  box-shadow: var(--shadow-card);
  overflow: hidden;
}

.readiness-head {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border: 0;
  background: transparent;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s ease;
}

.readiness-head:hover {
  background: var(--color-bg-surface-muted);
}

.traffic-light {
  flex-shrink: 0;
  width: 14px;
  height: 14px;
  border-radius: 50%;
  box-shadow: inset 0 0 0 2px rgba(255, 255, 255, 0.35);
}

.traffic-light.green {
  background: #22c55e;
  box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.2);
}

.traffic-light.red {
  background: #ef4444;
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.2);
  animation: pulse-red 2s ease-in-out infinite;
}

@keyframes pulse-red {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.72;
  }
}

.head-copy {
  flex: 1;
  min-width: 0;
}

.readiness-head h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 800;
  color: var(--color-text-strong);
}

.readiness-desc {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--color-text-muted);
}

.readiness-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  max-width: 220px;
}

.readiness-progress :deep(.el-progress) {
  flex: 1;
}

.readiness-progress-label {
  flex-shrink: 0;
  font-size: 11px;
  color: var(--color-text-subtle);
}

.readiness-badge {
  flex-shrink: 0;
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 999px;
}

.readiness-badge.ok {
  background: #ecfdf3;
  color: #15803d;
}

.readiness-badge.pending {
  background: #fff7ed;
  color: #c2410c;
}

.collapse-chevron {
  flex-shrink: 0;
  font-size: 14px;
  color: var(--color-text-subtle);
  transition: transform 0.2s ease;
}

.collapse-chevron.open {
  transform: rotate(180deg);
}

.vector-warn-banner {
  margin: 0 16px 12px;
}

.vector-warn-banner p {
  margin: 4px 0 8px;
  font-size: 13px;
  line-height: 1.5;
}

.readiness-cards {
  display: flex;
  flex-wrap: nowrap;
  gap: 10px;
  overflow-x: auto;
  padding: 0 16px 16px;
  scrollbar-width: thin;
}

.readiness-chip {
  flex: 1 1 0;
  min-width: 108px;
  max-width: 180px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  padding: 12px 12px 10px;
  border: 1px solid var(--color-border-subtle);
  border-radius: 10px;
  background: var(--color-bg-surface-muted);
  cursor: pointer;
  text-align: left;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.readiness-chip:hover {
  border-color: rgba(198, 111, 79, 0.45);
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06);
}

.readiness-chip.ok {
  border-color: rgba(22, 163, 74, 0.35);
  background: #f0fdf4;
}

.readiness-chip.warn {
  border-color: rgba(217, 119, 6, 0.35);
  background: #fffbeb;
}

.readiness-chip.no {
  border-color: rgba(248, 113, 113, 0.35);
  background: #fff5f5;
}

.chip-icon {
  font-size: 18px;
}

.readiness-chip.ok .chip-icon {
  color: var(--color-success);
}

.readiness-chip.warn .chip-icon {
  color: var(--color-warning);
}

.readiness-chip.no .chip-icon {
  color: #f87171;
}

.chip-label {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text-strong);
  line-height: 1.3;
}

.chip-hint {
  font-size: 11px;
  line-height: 1.35;
  color: var(--color-text-subtle);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

@media (max-width: 900px) {
  .readiness-cards {
    flex-wrap: wrap;
    overflow-x: visible;
  }

  .readiness-chip {
    flex: 1 1 calc(33.33% - 10px);
    max-width: none;
  }
}
</style>