<script setup lang="ts">
import { onMounted, ref } from 'vue'

withDefaults(
  defineProps<{
    compact?: boolean
    hideRecentRounds?: boolean
  }>(),
  {
    compact: false,
    hideRecentRounds: false,
  },
)
import { ElMessage } from 'element-plus'
import { getCostSummary } from '../api'
import { formatCnyYuan } from '../utils/tokenCostEstimate'

type CostSummary = {
  project_id?: string
  persisted?: {
    call_count: number
    total_tokens: number
    total_cost_cny: number
    today_tokens: number
    today_cost_cny: number
  }
  persisted_error?: string | null
  recent_rounds?: Array<{ round?: number; tokens_used?: number; chapters_completed?: number }>
  disclaimer?: string
}

const loading = ref(false)
const summary = ref<CostSummary | null>(null)
const loadError = ref('')

const load = async () => {
  loading.value = true
  loadError.value = ''
  try {
    const { data } = await getCostSummary()
    summary.value = data
    if (data?.persisted_error) {
      loadError.value = `费用落库读取异常：${data.persisted_error}`
    }
  } catch (error: any) {
    summary.value = null
    loadError.value = error?.message || '费用摘要加载失败'
    ElMessage.warning(loadError.value)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <section
    class="cost-summary-panel panel"
    :class="{ 'cost-summary-panel--compact': compact }"
    v-loading="loading"
  >
    <div class="cost-head">
      <div>
        <h3>费用摘要</h3>
        <p class="cost-hint">落库实耗（SQLite llm_cost_log）与最近连写轮 tokens</p>
      </div>
      <el-button size="small" text @click="load">刷新</el-button>
    </div>
    <el-alert
      v-if="loadError"
      type="warning"
      :closable="false"
      show-icon
      :title="loadError"
      class="cost-error-alert"
    />
    <div v-if="summary && !loadError" class="cost-grid">
      <div class="cost-stat">
        <span class="label">今日 tokens</span>
        <strong>{{ summary.persisted?.today_tokens ?? 0 }}</strong>
        <small>{{ formatCnyYuan(summary.persisted?.today_cost_cny ?? 0) }}</small>
      </div>
      <div class="cost-stat">
        <span class="label">本书累计 tokens</span>
        <strong>{{ summary.persisted?.total_tokens ?? 0 }}</strong>
        <small>{{ formatCnyYuan(summary.persisted?.total_cost_cny ?? 0) }}</small>
      </div>
      <div class="cost-stat">
        <span class="label">落库调用次数</span>
        <strong>{{ summary.persisted?.call_count ?? 0 }}</strong>
        <small>按章持久化</small>
      </div>
    </div>
    <ul v-if="!hideRecentRounds && summary?.recent_rounds?.length" class="round-list">
      <li v-for="(row, idx) in summary.recent_rounds" :key="idx">
        第 {{ row.round ?? '—' }} 轮 · {{ row.tokens_used ?? 0 }} tokens
        <template v-if="row.chapters_completed"> · {{ row.chapters_completed }} 章</template>
      </li>
    </ul>
    <p v-if="summary?.disclaimer && !loadError" class="cost-disclaimer">{{ summary.disclaimer }}</p>
  </section>
</template>

<style scoped>
.cost-summary-panel {
  padding: 14px 16px;
  margin-bottom: 0;
  flex-shrink: 0;
}

.cost-summary-panel--compact {
  padding: 10px 14px;
}

.cost-summary-panel--compact .cost-head {
  margin-bottom: 8px;
}

.cost-summary-panel--compact .cost-stat strong {
  font-size: 16px;
}

.cost-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}

.cost-head h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
}

.cost-hint {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--color-text-subtle);
}

.cost-error-alert {
  margin-bottom: 10px;
}

.cost-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.cost-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--color-bg-surface-muted);
  border: 1px solid var(--color-border-subtle);
}

.cost-stat .label {
  font-size: 11px;
  color: var(--color-text-subtle);
}

.cost-stat strong {
  font-size: 18px;
  color: var(--color-text-strong);
}

.cost-stat small {
  font-size: 11px;
  color: var(--color-text-muted);
}

.round-list {
  margin: 12px 0 0;
  padding-left: 18px;
  font-size: 12px;
  color: var(--color-text-muted);
}

.cost-disclaimer {
  margin: 10px 0 0;
  font-size: 11px;
  color: var(--color-text-subtle);
}

@media (max-width: 900px) {
  .cost-grid {
    grid-template-columns: 1fr;
  }
}
</style>