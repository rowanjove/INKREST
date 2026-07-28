<script setup lang="ts">
import { ref } from 'vue'
import { useTheme, type ThemeMode } from '../composables/useTheme'

const { themeMode, resolvedTheme, setThemeMode } = useTheme()
const expanded = ref(false)

const options: { value: ThemeMode; label: string; hint: string }[] = [
  { value: 'light', label: '浅色', hint: '日间默认' },
  { value: 'dark', label: '深色', hint: '夜间护眼' },
  { value: 'system', label: '跟随系统', hint: '随 OS 切换' },
]

const onChange = (mode: ThemeMode) => setThemeMode(mode)
</script>

<template>
  <section id="appearance" class="fold-card appearance-section">
    <div class="fold-head" @click="expanded = !expanded">
      <div class="head-left">
        <span class="collapse-arrow" :class="{ open: expanded }">▶</span>
        <div>
          <h2>外观与主题</h2>
          <p>
            全局界面亮/暗（侧栏、卡片、表单）；写作稿纸配色仍在写作页单独切换。
            当前：<strong>{{ resolvedTheme === 'dark' ? '深色' : '浅色' }}</strong>
            · {{ options.find((o) => o.value === themeMode)?.label ?? '浅色' }}
          </p>
        </div>
      </div>
    </div>
    <div v-show="expanded" class="fold-body">
      <el-radio-group
        :model-value="themeMode"
        class="theme-radio-group"
        @update:model-value="onChange"
      >
        <label
          v-for="opt in options"
          :key="opt.value"
          class="theme-option"
          :class="{ active: themeMode === opt.value }"
        >
          <el-radio :value="opt.value">{{ opt.label }}</el-radio>
          <span class="theme-hint">{{ opt.hint }}</span>
        </label>
      </el-radio-group>
    </div>
  </section>
</template>

<style scoped>
.appearance-section {
  scroll-margin-top: 72px;
}

.theme-radio-group {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  width: 100%;
}

.theme-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 16px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-surface);
  cursor: pointer;
  text-align: center;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.theme-option :deep(.el-radio) {
  margin-right: 0;
  height: auto;
}

.theme-option :deep(.el-radio__label) {
  font-size: 14px;
  font-weight: 700;
  padding-left: 6px;
}

.theme-option:hover {
  border-color: var(--color-primary);
}

.theme-option.active {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px rgba(198, 111, 79, 0.2);
  background: var(--color-primary-soft);
}

.theme-hint {
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.35;
}

@media (max-width: 720px) {
  .theme-radio-group {
    grid-template-columns: 1fr;
  }
}
</style>
