<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import PresetSelector from './PresetSelector.vue'
import type { Composition } from '../types/preset'
import {
  SCALE_OPTIONS,
  longFormScaleHint,
  targetChaptersInputMax,
} from '../constants/scaleOptions'

const props = defineProps<{
  initial?: {
    name?: string
    description?: string
    genre?: string
    target_chapters?: number
    scale?: string
    composition?: Composition | null
  }
}>()

const emit = defineEmits<{
  (e: 'create', data: {
    name: string
    description: string
    genre: string
    channel: string
    target_chapters: number
    scale: string
    scale_label: string
    target_chars_per_chapter: number[]
    composition: Composition | null
  }): void
}>()

const defaultScale = SCALE_OPTIONS[3]

const form = ref({
  name: '',
  description: '',
  genre: '',
  target_chapters: defaultScale.target_chapters,
  scale: defaultScale.scale,
  scale_label: defaultScale.label,
  chars_min: 2000,
  chars_max: 3000,
  composition: null as Composition | null,
})

const chaptersMax = computed(() => targetChaptersInputMax(form.value.scale))
const scaleHint = computed(() => longFormScaleHint(form.value.scale))

const applyInitial = (init?: typeof props.initial) => {
  if (!init) return
  if (init.name) form.value.name = init.name
  if (init.description) form.value.description = init.description
  if (init.genre) form.value.genre = init.genre
  if (init.composition) form.value.composition = init.composition
  if (init.target_chapters) form.value.target_chapters = init.target_chapters
  if (init.scale) {
    const opt = SCALE_OPTIONS.find((o) => o.scale === init.scale)
    if (opt) selectScale(opt)
  }
}

watch(() => props.initial, applyInitial, { immediate: true, deep: true })

const selectScale = (option: (typeof SCALE_OPTIONS)[number]) => {
  form.value.scale = option.scale
  form.value.scale_label = option.label
  form.value.target_chapters = option.target_chapters
  if (form.value.target_chapters > targetChaptersInputMax(option.scale)) {
    form.value.target_chapters = targetChaptersInputMax(option.scale)
  }
}

const handleSubmit = () => {
  if (!form.value.name.trim()) return
  const comp = form.value.composition
  emit('create', {
    name: form.value.name.trim(),
    description: form.value.description.trim(),
    genre: form.value.genre.trim() || comp?.theme || '',
    channel: comp?.channel || '',
    target_chapters: form.value.target_chapters,
    scale: form.value.scale,
    scale_label: form.value.scale_label,
    target_chars_per_chapter: [form.value.chars_min, form.value.chars_max],
    composition: comp,
  })
}

defineExpose({ handleSubmit, applyInitial })
</script>

<template>
  <div class="quick-form">
    <div class="form-section">
      <h3>基础信息</h3>
      <div class="form-grid">
        <div class="form-item full">
          <label>书名 <span class="required">*</span></label>
          <el-input
            v-model="form.name"
            placeholder="给你的作品起个名字"
            maxlength="50"
            show-word-limit
            @keyup.enter="handleSubmit"
          />
        </div>
        <div class="form-item full">
          <label>题材 / 频道（可选）</label>
          <el-input v-model="form.genre" placeholder="如：都市、玄幻；或由下方套路模板带入" />
        </div>
        <div class="form-item full">
          <label>简介</label>
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="核心主题与卖点（会写入大纲骨架，便于后续生成）"
            maxlength="500"
            show-word-limit
          />
        </div>
      </div>
    </div>

    <div class="form-section">
      <h3>写作规模</h3>
      <div class="scale-options">
        <button
          v-for="option in SCALE_OPTIONS"
          :key="option.scale"
          type="button"
          :class="['scale-option', { active: form.scale === option.scale }]"
          @click="selectScale(option)"
        >
          <strong>{{ option.label }}</strong>
          <small>{{ option.hint }}</small>
        </button>
      </div>
      <p v-if="scaleHint" class="scale-long-hint">{{ scaleHint }}</p>
      <p
        v-if="form.scale === 'micro' || form.scale === 'short'"
        class="scale-long-hint"
      >
        快速创建仅写入最小卷纲骨架，适合微型/短篇；保存后可直接工作台开跑。
      </p>
      <p v-else class="scale-long-hint outline-warn">
        中长篇/超长篇：快速创建后请到大纲页用「生成大纲」走总编（含体量约束与分段卷纲），再「同步卷队列」后自动生成。
      </p>
      <div class="form-grid">
        <div class="form-item">
          <label>目标章节数</label>
          <el-input-number
            v-model="form.target_chapters"
            :min="1"
            :max="chaptersMax"
            :step="form.scale === 'infinite' ? 100 : 50"
          />
        </div>
        <div class="form-item">
          <label>每章字数范围</label>
          <div class="chars-range">
            <el-input-number v-model="form.chars_min" :min="200" :max="5000" :step="100" size="small" />
            <span class="range-sep">~</span>
            <el-input-number v-model="form.chars_max" :min="200" :max="5000" :step="100" size="small" />
            <span class="range-unit">字</span>
          </div>
        </div>
      </div>
    </div>

    <div class="form-section">
      <h3>预设模板</h3>
      <PresetSelector v-model="form.composition" />
    </div>
  </div>
</template>

<style scoped>
.quick-form {
  display: grid;
  gap: 28px;
}

.form-section h3 {
  margin: 0 0 14px;
  color: #1f2937;
  font-size: 16px;
  font-weight: 600;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
}

.scale-options {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}

.outline-warn {
  color: #b45309;
}

.scale-long-hint {
  margin: 0 0 14px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #fff8f4;
  border: 1px solid #f0d5c8;
  color: #9a5033;
  font-size: 13px;
  line-height: 1.5;
}

.scale-option {
  display: grid;
  gap: 4px;
  min-height: 64px;
  padding: 10px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: var(--color-bg-surface);
  color: #374151;
  text-align: left;
  cursor: pointer;
}

.scale-option:hover,
.scale-option.active {
  border-color: #c66f4f;
  background: #fff8f4;
}

.scale-option strong {
  font-size: 13px;
}

.scale-option small {
  color: #9ca3af;
  font-size: 12px;
}

.form-item {
  display: grid;
  align-content: start;
  gap: 6px;
}

.form-item.full {
  grid-column: 1 / -1;
}

.form-item label {
  color: #374151;
  font-size: 14px;
  font-weight: 500;
}

.required {
  color: var(--color-danger);
}

.chars-range {
  display: flex;
  align-items: center;
  gap: 8px;
}

.range-sep,
.range-unit {
  color: #6b7280;
  font-size: 13px;
}
</style>