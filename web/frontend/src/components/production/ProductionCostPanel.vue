<script setup lang="ts">
import { computed } from 'vue'
import type { CostSummary } from '../../entities/project/projectSnapshot'

const props = defineProps<{ summary: CostSummary }>()
const persisted = computed(() => props.summary.persisted || ({} as any))
const integer = (value: unknown) => Number(value || 0).toLocaleString()
const money = (value: unknown) => Number(value || 0).toFixed(4)

const callCount = computed(() => Number(persisted.value?.call_count || 0))
const totalTokens = computed(() => Number(persisted.value?.total_tokens || 0))
const totalCost = computed(() => Number(persisted.value?.total_cost_cny || 0))
const latestCall = computed(() => persisted.value?.last_call_at || persisted.value?.last_event_at || '')

const costStatusText = computed(() => {
  if (callCount.value === 0) return '尚无调用'
  if (totalTokens.value === 0) return '未返回用量'
  return `¥${money(totalCost.value)}`
})

const tokenStatusSub = computed(() => {
  if (callCount.value === 0) return '尚无调用记录'
  if (totalTokens.value === 0) return '供应商未返回 Token 用量'
  return `输入 ${integer(persisted.value.input_tokens)} · 输出 ${integer(persisted.value.output_tokens)}`
})
</script>

<template>
  <section class="cost-workspace">
    <div class="cost-cards">
      <article>
        <span>累计费用</span>
        <strong>{{ costStatusText }}</strong>
        <small>本项目持久化统计</small>
      </article>
      <article>
        <span>今日费用</span>
        <strong>¥{{ money(persisted.today_cost_cny) }}</strong>
        <small>{{ integer(persisted.today_tokens) }} tokens</small>
      </article>
      <article>
        <span>累计 Token</span>
        <strong>{{ integer(totalTokens) }}</strong>
        <small>{{ tokenStatusSub }}</small>
      </article>
      <article>
        <span>模型调用</span>
        <strong>{{ integer(callCount) }} 次</strong>
        <small v-if="latestCall">最新: {{ latestCall }}</small>
        <small v-else>仅统计已落库调用</small>
      </article>
    </div>

    <article class="round-panel">
      <header><h2>最近生产轮次</h2><span>{{ summary.recent_rounds?.length || 0 }}</span></header>
      <div v-if="summary.persisted_error" class="cost-warning">{{ summary.persisted_error }}</div>
      <div v-if="summary.recent_rounds?.length" class="round-table">
        <div v-for="(round, index) in summary.recent_rounds" :key="String(round.id || round.ts || index)">
          <strong>{{ round.label || round.ts || `轮次 ${index + 1}` }}</strong>
          <span>{{ integer(round.total_tokens || round.tokens_used) }} tokens</span>
          <span>¥{{ money(round.total_cost_cny || round.cost_cny) }}</span>
        </div>
      </div>
      <p v-else class="empty-copy">尚无持久化生产轮次费用。</p>
      <footer>{{ summary.disclaimer || '费用按模型配置与已记录 token 估算，仅供本地创作预算参考。' }}</footer>
    </article>
  </section>
</template>

<style scoped>
.cost-workspace { height: 100%; min-height: 0; overflow: auto; padding: 16px; }
.cost-cards { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
.cost-cards article, .round-panel { padding: 15px; border: 1px solid var(--color-border); border-radius: var(--radius-lg); background: var(--color-bg-surface); box-shadow: var(--shadow-sm); }
.cost-cards article { display: grid; gap: 7px; }
.cost-cards span { color: var(--color-text-muted); font-size: 12.5px; }
.cost-cards strong { color: var(--color-text-strong); font-size: 22px; }
.cost-cards small { color: var(--color-text-muted); font-size: 12px; }
.round-panel { margin-top: 14px; }
.round-panel header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.round-panel h2 { margin: 0; color: var(--color-text-strong); font-size: 15px; font-weight: 750; }
.round-panel header span { color: var(--color-text-muted); font-size: 12px; }
.round-table { display: grid; }
.round-table > div { display: grid; grid-template-columns: minmax(0, 1fr) auto auto; gap: 18px; padding: 11px 0; border-bottom: 1px solid var(--color-border-subtle); color: var(--color-text-muted); font-size: 13px; }
.round-table strong { color: var(--color-text-strong); }
.cost-warning { padding: 10px 12px; border-radius: 7px; background: var(--color-alert-warn-bg); color: var(--color-warning); font-size: 12.5px; }
.empty-copy, footer { color: var(--color-text-muted); font-size: 12.5px; line-height: 1.6; }
footer { margin-top: 14px; }
@media (max-width: 1100px) { .cost-cards { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
</style>
