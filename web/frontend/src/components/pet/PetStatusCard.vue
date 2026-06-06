<script setup lang="ts">
import { computed } from 'vue'
import type { AssistantContext } from '../../stores/pet'

const props = defineProps<{
  context: AssistantContext | null
  status: string
  error?: string
}>()

const projectName = computed(() => props.context?.active_project?.name || '未选择项目')
const runningTask = computed(() => props.context?.running_tasks?.[0] || null)
const failedTask = computed(() => {
  const failed = props.context?.failed_tasks || []
  return failed.length ? failed[failed.length - 1] : null
})
const detail = computed(() => {
  if (props.error) return props.error
  if (runningTask.value) {
    return `${runningTask.value.chapter_id || '章节'} · ${runningTask.value.step || '运行中'}`
  }
  if (failedTask.value) {
    return failedTask.value.error || '最近有任务失败'
  }
  return '我在这里看着任务队列，有动静就提醒你。'
})
</script>

<template>
  <section class="pet-status-card">
    <div class="status-topline">
      <span class="status-dot" :class="{ alert: failedTask || error, busy: runningTask }" />
      <strong>{{ status }}</strong>
    </div>
    <h2>{{ projectName }}</h2>
    <p>{{ detail }}</p>
  </section>
</template>

<style scoped>
.pet-status-card {
  display: grid;
  gap: 8px;
  padding: 14px;
  border: 1px solid #e4eaf2;
  border-radius: 8px;
  background: var(--color-bg-surface);
}

.status-topline {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #667085;
  font-size: 13px;
}

.status-dot {
  width: 9px;
  height: 9px;
  border-radius: 999px;
  background: #48a868;
  box-shadow: 0 0 0 3px rgba(72, 168, 104, 0.14);
}

.status-dot.busy {
  background: #4f7fc6;
  box-shadow: 0 0 0 3px rgba(79, 127, 198, 0.14);
}

.status-dot.alert {
  background: #d65d5d;
  box-shadow: 0 0 0 3px rgba(214, 93, 93, 0.14);
}

h2 {
  margin: 0;
  color: #1f2937;
  font-size: 18px;
}

p {
  margin: 0;
  color: #536176;
  font-size: 13px;
  line-height: 1.55;
}
</style>
