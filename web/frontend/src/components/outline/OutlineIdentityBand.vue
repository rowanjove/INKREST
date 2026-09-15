<script setup lang="ts">
const props = withDefaults(defineProps<{
  chosenTitle?: string
  title?: string
  logline?: string
  titleOptions?: string[]
  customTitle?: string
  loading?: boolean
  onSelectTitle: (title: string) => void
}>(), {
  chosenTitle: '',
  title: '未命名作品',
  logline: '还没有一句话梗概',
  titleOptions: () => [],
  customTitle: '',
  loading: false,
})

const emit = defineEmits<{
  'update:customTitle': [value: string]
}>()

function selectCustomTitle() {
  props.onSelectTitle(props.customTitle.trim())
}
</script>

<template>
  <section class="identity-band" aria-labelledby="outline-identity-title">
    <div class="identity-copy">
      <span class="identity-label">{{ chosenTitle ? '最终书名' : '书名未定' }}</span>
      <h2 id="outline-identity-title">{{ chosenTitle || title }}</h2>
      <p>{{ logline }}</p>
    </div>

    <div v-if="!chosenTitle" class="title-picker" aria-label="确定最终书名">
      <span class="picker-hint">先选一个书名，之后才能开始生产。</span>
      <div class="picker-options">
        <button
          v-for="option in titleOptions"
          :key="option"
          type="button"
          class="title-option"
          :disabled="loading"
          @click="onSelectTitle(option)"
        >
          {{ option }}
        </button>
        <el-input
          :model-value="customTitle"
          size="small"
          class="custom-title-input"
          placeholder="输入自定义书名"
          @update:model-value="emit('update:customTitle', $event)"
          @keyup.enter="selectCustomTitle"
        >
          <template #append>
            <el-button size="small" :loading="loading" @click="selectCustomTitle">确定</el-button>
          </template>
        </el-input>
      </div>
    </div>
  </section>
</template>

<style scoped>
.identity-band {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: end;
  gap: 20px;
  padding: 4px 0 14px;
  border-bottom: 1px solid var(--color-border-subtle);
}
.identity-copy { min-width: 0; }
.identity-label {
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 700;
}
.identity-copy h2 {
  margin: 3px 0 5px;
  color: var(--color-text-strong);
  font-size: 22px;
  line-height: 1.25;
  overflow-wrap: anywhere;
}
.identity-copy p {
  max-width: 680px;
  margin: 0;
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 1.55;
}
.title-picker {
  min-width: min(100%, 480px);
  display: grid;
  gap: 7px;
}
.picker-hint { color: var(--color-text-muted); font-size: 11px; }
.picker-options { display: flex; align-items: center; justify-content: flex-end; gap: 7px; flex-wrap: wrap; }
.title-option {
  padding: 5px 10px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  background: var(--color-bg-surface);
  color: var(--color-text);
  font: inherit;
  font-size: 12px;
  cursor: pointer;
}
.title-option:hover:not(:disabled) { border-color: var(--color-primary); color: var(--color-primary); }
.title-option:disabled { cursor: wait; opacity: .6; }
.custom-title-input { width: 220px; }
@media (max-width: 760px) {
  .identity-band { grid-template-columns: 1fr; align-items: start; }
  .title-picker { min-width: 0; }
  .picker-options { justify-content: flex-start; }
  .custom-title-input { width: min(100%, 260px); }
}
</style>

