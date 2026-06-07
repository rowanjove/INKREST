/** Rough batch cost estimate from model library pricing hints. */

export const TOKENS_PER_CHAPTER_ESTIMATE = 12_000
const DEFAULT_BLENDED_CNY_PER_1K = 0.0144 // ~0.002 USD blended × 7.2

type ModelEntry = {
  id?: string
  model?: string
  name?: string
  blended_price_per_1k_cny?: number
}

type LlmConfig = {
  daily_model_id?: string
  default_model_id?: string
  default?: { model_ref?: string }
}

export function resolveDailyModelRef(config: { llm?: LlmConfig } | null | undefined): string {
  const llm = config?.llm || {}
  return llm.daily_model_id || llm.default_model_id || llm.default?.model_ref || ''
}

export function resolveDailyModelPricePer1k(
  config: { llm?: LlmConfig } | null | undefined,
  models: ModelEntry[],
): { pricePer1k: number; modelLabel: string } {
  const ref = resolveDailyModelRef(config)
  const byId = new Map(models.map((m) => [m.id || '', m]))
  const picked = ref ? byId.get(ref) : undefined
  const pricePer1k =
    typeof picked?.blended_price_per_1k_cny === 'number' && picked.blended_price_per_1k_cny > 0
      ? picked.blended_price_per_1k_cny
      : DEFAULT_BLENDED_CNY_PER_1K
  const modelLabel = picked
    ? picked.name || picked.model || ref
    : ref
      ? `未知模型（${ref}）`
      : '默认模型'
  return { pricePer1k, modelLabel }
}

export function formatTokenEstimate(tokens: number): string {
  if (tokens <= 0) return '—'
  if (tokens >= 1_000_000) return `约 ${(tokens / 1_000_000).toFixed(1)}M tokens`
  if (tokens >= 1000) return `约 ${Math.round(tokens / 1000)}k tokens`
  return `约 ${tokens} tokens`
}

export function formatCnyEstimate(cny: number): string {
  if (cny <= 0) return '—'
  if (cny >= 1) return `约 ¥${cny.toFixed(1)}`
  return `约 ¥${(cny * 100).toFixed(0)} 分`
}

export function estimateBatchTokenCost(
  chapters: number,
  pricePer1k: number,
): { chapters: number; tokens: number; label: string; priceLabel: string; cny: number } {
  const n = Math.max(0, Math.floor(chapters))
  if (n <= 0) {
    return { chapters: 0, tokens: 0, label: '—', priceLabel: '—', cny: 0 }
  }
  const tokens = n * TOKENS_PER_CHAPTER_ESTIMATE
  const cny = (tokens / 1000) * pricePer1k
  return {
    chapters: n,
    tokens,
    label: formatTokenEstimate(tokens),
    priceLabel: formatCnyEstimate(cny),
    cny,
  }
}