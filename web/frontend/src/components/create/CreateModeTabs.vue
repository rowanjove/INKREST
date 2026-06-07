<script setup lang="ts">
import { Cpu, Document, Lightning, MagicStick } from '@element-plus/icons-vue'
import type { CreateMode } from '../../composables/useCreateWizard'

defineProps<{
  aiModelReady: boolean
  aiModelLabel: string
}>()

const activeMode = defineModel<CreateMode>('activeMode', { required: true })

const emit = defineEmits<{
  goToConfig: []
}>()
</script>

<template>
  <div class="mode-tabs">
    <button class="mode-tab" :class="{ active: activeMode === 'quick' }" @click="activeMode = 'quick'">
      <el-icon :size="20"><Lightning /></el-icon>
      <div>
        <strong>快速创建</strong>
        <small>填写表单，直接开始</small>
      </div>
      <el-tag size="small" type="warning" effect="dark" class="rec-tag">默认</el-tag>
    </button>
    <button class="mode-tab" :class="{ active: activeMode === 'parse' }" @click="activeMode = 'parse'">
      <el-icon :size="20"><Document /></el-icon>
      <div>
        <strong>内容分析导入</strong>
        <small>粘贴文字/上传草稿解析建档</small>
      </div>
    </button>
    <button class="mode-tab" :class="{ active: activeMode === 'ai' }" @click="activeMode = 'ai'">
      <el-icon :size="20"><MagicStick /></el-icon>
      <div>
        <strong>AI 创作引导</strong>
        <small>和 AI 聊几步自动构建雏形</small>
      </div>
    </button>
  </div>

  <div v-if="activeMode === 'ai'" class="engine-mini" :class="{ ready: aiModelReady }">
    <el-icon><Cpu /></el-icon>
    <span>{{ aiModelReady ? `AI 引导模型：${aiModelLabel}` : 'AI 引导模型未就绪' }}</span>
    <el-button text size="small" @click="emit('goToConfig')">模型设置</el-button>
  </div>
</template>

<style scoped>
.mode-tabs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.mode-tab {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 76px;
  padding: 16px 20px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  background: var(--color-bg-surface);
  color: #374151;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s;
}

.mode-tab:hover,
.mode-tab.active {
  border-color: #c66f4f;
  box-shadow: 0 4px 16px rgba(198, 111, 79, 0.12);
}

.mode-tab .el-icon {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: #f3f4f6;
  color: #6b7280;
}

.mode-tab.active .el-icon {
  background: #c66f4f;
  color: var(--color-bg-surface);
}

.mode-tab div {
  display: grid;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.mode-tab strong {
  font-size: 14px;
}

.mode-tab small {
  color: #9ca3af;
  font-size: 11px;
}

.rec-tag {
  margin-left: auto;
}

.engine-mini {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid #f3d1c4;
  border-radius: 8px;
  background: #fff7f3;
  color: #9a3412;
  font-size: 13px;
}

.engine-mini.ready {
  border-color: #bbf7d0;
  background: #f0fdf4;
  color: #166534;
}
</style>