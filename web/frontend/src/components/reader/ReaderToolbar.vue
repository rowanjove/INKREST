<script setup lang="ts">
import { ArrowLeft, ArrowRight, CaretTop, Menu, Setting } from '@element-plus/icons-vue'
import type { ReaderSettings } from '../../composables/useReaderView'

defineProps<{
  selectedIndex: number
  chapterCount: number
  settings: ReaderSettings
}>()

const drawerVisible = defineModel<boolean>('drawerVisible', { required: true })

const emit = defineEmits<{
  goChapter: [offset: number]
  scrollToTop: []
}>()
</script>

<template>
  <div class="floating-toolbar">
    <el-tooltip content="目录 (Catalog)" placement="right">
      <button class="tool-btn" @click="drawerVisible = true">
        <el-icon><Menu /></el-icon>
      </button>
    </el-tooltip>

    <el-popover placement="right" trigger="click" width="300" popper-class="reader-settings-popover">
      <template #reference>
        <button class="tool-btn">
          <el-icon><Setting /></el-icon>
        </button>
      </template>

      <div class="settings-panel">
        <h3>阅读器设置</h3>

        <div class="settings-item">
          <span>配色主题</span>
          <el-segmented
            v-model="settings.theme"
            :options="[
              { label: '宣纸', value: 'paper' },
              { label: '雅白', value: 'light' },
              { label: '护眼', value: 'green' },
              { label: '夜间', value: 'dark' },
            ]"
            size="small"
          />
        </div>

        <div class="settings-item">
          <span>系统字号 (px)</span>
          <el-input-number
            v-model="settings.fontSize"
            :min="14"
            :max="32"
            :step="1"
            size="small"
            controls-position="right"
          />
        </div>

        <div class="settings-item">
          <span>文字行高</span>
          <el-input-number
            v-model="settings.lineHeight"
            :min="1.4"
            :max="2.5"
            :step="0.1"
            :precision="1"
            size="small"
            controls-position="right"
          />
        </div>

        <div class="settings-item">
          <span>阅读宽度 (px)</span>
          <el-slider
            v-model="settings.width"
            :min="600"
            :max="1000"
            :step="40"
            style="flex: 1; margin-left: 10px"
          />
        </div>

        <div class="settings-item">
          <span>首行缩进</span>
          <el-switch v-model="settings.indent" active-color="#c66f4f" />
        </div>
      </div>
    </el-popover>

    <div class="divider" />

    <el-tooltip content="上一章" placement="right">
      <button class="tool-btn" :disabled="selectedIndex <= 0" @click="emit('goChapter', -1)">
        <el-icon><ArrowLeft /></el-icon>
      </button>
    </el-tooltip>

    <el-tooltip content="下一章" placement="right">
      <button
        class="tool-btn"
        :disabled="selectedIndex < 0 || selectedIndex >= chapterCount - 1"
        @click="emit('goChapter', 1)"
      >
        <el-icon><ArrowRight /></el-icon>
      </button>
    </el-tooltip>

    <el-tooltip content="回到顶部" placement="right">
      <button class="tool-btn" @click="emit('scrollToTop')">
        <el-icon><CaretTop /></el-icon>
      </button>
    </el-tooltip>
  </div>
</template>

<style scoped>
.floating-toolbar {
  position: fixed;
  left: 310px;
  top: 120px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 10px;
  background: white;
  border: 1px solid var(--border-light);
  border-radius: 99px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
  z-index: 100;
}

.tool-btn {
  width: 42px;
  height: 42px;
  border-radius: 99px;
  border: none;
  background: transparent;
  color: #4b5563;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 18px;
}

.tool-btn:hover:not(:disabled) {
  background: var(--color-bg-hover);
  color: var(--primary);
  transform: scale(1.05);
}

.tool-btn:disabled {
  color: #d1d5db;
  cursor: not-allowed;
}

.floating-toolbar .divider {
  height: 1px;
  background: var(--color-border);
  margin: 4px 6px;
}

.settings-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 6px;
}

.settings-panel h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 800;
  color: var(--color-text-strong);
  border-bottom: 1px solid var(--color-bg-hover);
  padding-bottom: 8px;
}

.settings-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13.5px;
  color: var(--color-text-muted);
}

@media (max-width: 1200px) {
  .floating-toolbar {
    left: 20px;
    top: auto;
    bottom: 40px;
    flex-direction: row;
    border-radius: 99px;
    padding: 6px 14px;
  }

  .floating-toolbar .divider {
    width: 1px;
    height: 24px;
    margin: 6px 4px;
  }
}
</style>