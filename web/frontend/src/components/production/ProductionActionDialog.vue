<script setup lang="ts">
import { WarningFilled } from '@element-plus/icons-vue'
import type { ProductionActionIntent } from '../../entities/production/production'

defineProps<{
  modelValue: boolean
  intent: ProductionActionIntent | null
  loading?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  confirm: []
}>()
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    width="min(520px, calc(100vw - 32px))"
    :close-on-click-modal="!loading"
    :close-on-press-escape="!loading"
    :show-close="!loading"
    aria-label="生产动作确认"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <template #header>
      <div class="dialog-title">
        <el-icon><WarningFilled /></el-icon>
        <div><small>确认生产动作</small><strong>{{ intent?.label }}</strong></div>
      </div>
    </template>
    <div v-if="intent" class="intent-copy">
      <p>{{ intent.description }}</p>
      <dl>
        <div v-if="intent.chapterIds.length">
          <dt>影响范围</dt>
          <dd>{{ intent.chapterIds.map((id) => `第 ${id} 章`).join('、') }}</dd>
        </div>
        <div v-if="intent.taskId">
          <dt>任务</dt>
          <dd>{{ intent.taskId }}</dd>
        </div>
        <div>
          <dt>执行时机</dt>
          <dd>只有点击下方确认按钮后才会提交</dd>
        </div>
      </dl>
    </div>
    <template #footer>
      <el-button :disabled="loading" @click="emit('update:modelValue', false)">取消</el-button>
      <el-button
        :type="intent?.tone === 'danger' ? 'danger' : intent?.tone === 'warning' ? 'warning' : 'primary'"
        :loading="loading"
        @click="emit('confirm')"
      >
        {{ intent?.confirmLabel || '确认' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.dialog-title { display: flex; align-items: center; gap: 10px; color: var(--color-warning); }
.dialog-title > div { display: grid; gap: 2px; }
.dialog-title small { color: var(--color-text-muted); font-size: 10px; }
.dialog-title strong { color: var(--color-text-strong); font-size: 16px; }
.intent-copy { display: grid; gap: 14px; }
.intent-copy > p {
  margin: 0;
  padding: 12px;
  border-left: 3px solid var(--color-warning);
  background: var(--color-alert-warn-bg);
  color: var(--color-text);
  font-size: 12px;
  line-height: 1.7;
}
dl { display: grid; gap: 8px; margin: 0; }
dl > div { display: grid; grid-template-columns: 70px minmax(0, 1fr); gap: 10px; }
dt { color: var(--color-text-muted); font-size: 11px; }
dd { margin: 0; color: var(--color-text-strong); font-size: 11px; line-height: 1.6; }
</style>
