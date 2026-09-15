<script setup lang="ts">
import { ref, watch } from 'vue'
import type { ChapterProgress } from '../../entities/project/projectSnapshot'
import type { OutlineQueueStatus } from '../../entities/outline/outlineQueueStatus'
import ProgressMetricDetails from './ProgressMetricDetails.vue'
import OutlineQueueDetails from './OutlineQueueDetails.vue'

const props = defineProps<{
  modelValue: boolean
  progress: ChapterProgress
  queue: OutlineQueueStatus | null
}>()

const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()
const activeTab = ref('progress')

watch(() => props.modelValue, (visible) => {
  if (visible) activeTab.value = 'progress'
})
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    title="进度详情"
    width="min(720px, calc(100vw - 32px))"
    align-center
    @update:model-value="emit('update:modelValue', $event)"
  >
    <el-tabs v-model="activeTab" aria-label="进度详情子页">
      <el-tab-pane label="进度口径" name="progress">
        <ProgressMetricDetails :progress="progress" />
      </el-tab-pane>
      <el-tab-pane label="卷队列" name="queue">
        <OutlineQueueDetails :status="queue" />
      </el-tab-pane>
    </el-tabs>
  </el-dialog>
</template>

