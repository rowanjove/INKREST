<script setup lang="ts">
import type { useTasksStore } from '../../stores/tasks'

const repairDialogVisible = defineModel<boolean>('repairDialogVisible', { required: true })

defineProps<{
  tasksStore: ReturnType<typeof useTasksStore>
  repairForm: { chapter_id: string; goal: string }
  repairing: boolean
  suggestingGoal: boolean
  onSuggestGoal: () => void
  onSubmitRepair: () => void
}>()
</script>

<template>
  <el-dialog v-model="repairDialogVisible" :title="`补齐 ${repairForm.chapter_id}`" width="500px">
    <el-form :model="repairForm" label-position="top">
      <el-form-item required>
        <template #label>
          <div style="display: flex; justify-content: space-between; align-items: center; width: 100%">
            <span>本章写作目标 (Goal)</span>
            <el-button
              type="primary"
              link
              :loading="suggestingGoal"
              :disabled="tasksStore.isRunning || suggestingGoal"
              @click="onSuggestGoal"
            >
              AI 读入大纲
            </el-button>
          </div>
        </template>
        <el-input
          v-model="repairForm.goal"
          type="textarea"
          :rows="5"
          placeholder="描述该章发展脉络或写作要求"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="repairDialogVisible = false">取消</el-button>
      <el-button
        type="primary"
        :loading="repairing"
        :disabled="tasksStore.isRunning || repairing"
        @click="onSubmitRepair"
      >
        运行章节流水线
      </el-button>
    </template>
  </el-dialog>
</template>