<script setup lang="ts">
import QuickCreateForm from '../QuickCreateForm.vue'

defineProps<{
  creating: boolean
}>()

const quickFormRef = defineModel<InstanceType<typeof QuickCreateForm> | null>('quickFormRef')

const emit = defineEmits<{
  goBack: []
  quickCreate: [data: {
    name: string
    description: string
    genre: string
    channel: string
    target_chapters: number
    scale: string
    scale_label: string
    target_chars_per_chapter: number[]
    composition: {
      channel: string
      theme: string
      mechanisms: string[]
      cool_points: string[]
    } | null
  }]
  triggerSubmit: []
}>()
</script>

<template>
  <div class="quick-wrapper">
    <QuickCreateForm
      :ref="(el) => { quickFormRef = el as InstanceType<typeof QuickCreateForm> | null }"
      @create="emit('quickCreate', $event)"
    />
    <div class="quick-footer">
      <el-button @click="emit('goBack')">取消</el-button>
      <el-button type="primary" :loading="creating" @click="emit('triggerSubmit')">继续确认建档</el-button>
    </div>
  </div>
</template>

<style scoped>
.quick-wrapper {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: var(--color-bg-surface);
  padding: 24px;
}

.quick-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #eef2f7;
}
</style>
