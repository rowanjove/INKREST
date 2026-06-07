<script setup lang="ts">
import { Setting } from '@element-plus/icons-vue'
import AiChatGuide from '../AiChatGuide.vue'

defineProps<{
  aiModelReady: boolean
  aiModelLabel: string
}>()

const emit = defineEmits<{
  switchToQuick: []
  goToConfig: []
  aiComplete: [data: {
    name: string
    description: string
    genre: string
    context: Record<string, unknown>
  }]
}>()
</script>

<template>
  <div v-if="!aiModelReady" class="no-model-warning">
    <h3>尚未配置 LLM 模型</h3>
    <p>AI 创作引导需要至少一个可用模型。你仍然可以使用快速创建或内容分析导入。</p>
    <div class="warning-actions">
      <el-button @click="emit('switchToQuick')">切换到快速创建</el-button>
      <el-button type="primary" :icon="Setting" @click="emit('goToConfig')">去设置</el-button>
    </div>
  </div>
  <AiChatGuide v-else :model-label="aiModelLabel" @complete="emit('aiComplete', $event)" />
</template>

<style scoped>
.no-model-warning {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: var(--color-bg-surface);
  padding: 24px;
}

.no-model-warning h3 {
  margin: 0 0 8px;
  color: #111827;
}

.no-model-warning p {
  margin: 0;
  color: #6b7280;
}

.warning-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #eef2f7;
}
</style>