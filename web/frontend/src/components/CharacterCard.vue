<script setup lang="ts">
import { User } from '@element-plus/icons-vue'

defineProps<{
  name: string
  data: any
}>()
</script>

<template>
  <div class="character-card">
    <div class="card-header">
      <div class="avatar">
        <el-icon><User /></el-icon>
      </div>
      <div>
        <h3 class="char-name">{{ name }}</h3>
        <span class="char-role" v-if="data.role">{{ data.role }}</span>
      </div>
    </div>
    <div class="card-body">
      <div class="info-row" v-if="data.location">
        <span class="info-label">位置</span>
        <span class="info-value">{{ data.location }}</span>
      </div>
      <div class="info-row" v-if="data.emotion">
        <span class="info-label">情绪</span>
        <span class="info-value">{{ data.emotion }}</span>
      </div>
      <div class="info-row" v-if="data.physical_state">
        <span class="info-label">状态</span>
        <span class="info-value">{{ data.physical_state }}</span>
      </div>
      <div class="info-row" v-if="data.speech_style">
        <span class="info-label">语言风格</span>
        <span class="info-value">{{ data.speech_style }}</span>
      </div>
      <div class="constraints" v-if="data.constraints">
        <span class="info-label">约束条件</span>
        <p>{{ typeof data.constraints === 'string' ? data.constraints : JSON.stringify(data.constraints) }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.character-card {
  border: 1px solid var(--border-light);
  border-radius: 12px;
  background: var(--color-bg-surface);
  overflow: hidden;
  transition: all 0.25s ease;
}
.character-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}
.card-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  background: linear-gradient(135deg, #faf8f5, #f5f0eb);
  border-bottom: 1px solid var(--border-light);
}
.avatar {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: var(--primary-light);
  color: var(--primary);
  font-size: 20px;
}
.char-name {
  font-size: 16px;
  font-weight: 700;
  color: #1a2129;
}
.char-role {
  font-size: 12px;
  color: var(--text-muted);
}
.card-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.info-row {
  display: flex;
  gap: 12px;
}
.info-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  min-width: 56px;
  flex-shrink: 0;
}
.info-value {
  font-size: 13px;
  color: var(--text-main);
}
.constraints p {
  font-size: 12px;
  color: var(--text-muted);
  line-height: 1.5;
  margin-top: 4px;
}
</style>
