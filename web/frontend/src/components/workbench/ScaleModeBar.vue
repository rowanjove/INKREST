<script setup lang="ts">
import { computed } from 'vue'
import { longFormScaleHint, findScaleOption } from '../../constants/scaleOptions'

const props = defineProps<{
  scale?: string
  scaleLabel?: string
  targetChapters?: number
  chaptersWritten?: number
}>()

const scaleKey = computed(() => props.scale || '')
const hint = computed(() => longFormScaleHint(scaleKey.value))
const opt = computed(() => findScaleOption(scaleKey.value))

const modeTitle = computed(() => {
  const s = scaleKey.value
  if (s === 'micro' || s === 'short') return '短篇模式'
  if (s === 'medium') return '中篇模式'
  if (s === 'long') return '长篇模式'
  if (s === 'epic') return '超长篇模式'
  if (s === 'infinite') return '无限连载模式'
  return '标准模式'
})

const progressLine = computed(() => {
  const written = props.chaptersWritten ?? 0
  const target = props.targetChapters ?? 0
  if (!target) return `已写 ${written} 章`
  return `已写 ${written} / ${target} 章`
})
</script>

<template>
  <div v-if="scaleKey || scaleLabel" class="scale-mode-bar">
    <div class="mode-head">
      <strong>{{ modeTitle }}</strong>
      <span class="mode-label">{{ scaleLabel || opt?.label || scaleKey }}</span>
      <span class="mode-progress">{{ progressLine }}</span>
    </div>
    <p v-if="hint" class="mode-hint">{{ hint }}</p>
    <p v-else-if="scaleKey === 'micro' || scaleKey === 'short'" class="mode-hint muted">
      体量较小，工作台可一次多章自动生成，写完即进入阅读/导出。
    </p>
    <p v-else-if="scaleKey === 'medium'" class="mode-hint muted">
      建议每轮 5～20 章自动生成；门禁或外站不过时先在章节维护改稿，勿直接无上限续跑。
    </p>
  </div>
</template>

<style scoped>
.scale-mode-bar {
  margin-bottom: 14px;
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid #e8dfd8;
  background: linear-gradient(135deg, #fffaf7 0%, #fff 60%);
}

.mode-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px 14px;
}

.mode-head strong {
  color: #9a5033;
  font-size: 14px;
}

.mode-label {
  font-size: 13px;
  color: var(--color-text-muted);
}

.mode-progress {
  margin-left: auto;
  font-size: 13px;
  color: var(--color-text-muted);
}

.mode-hint {
  margin: 8px 0 0;
  font-size: 12.5px;
  line-height: 1.5;
  color: #9a5033;
}

.mode-hint.muted {
  color: var(--color-text-muted);
}
</style>