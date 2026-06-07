<script setup lang="ts">
import { Delete, Plus } from '@element-plus/icons-vue'
import { useTasksStore } from '../../stores/tasks'

type BatchRow = { chapter_id: string; goal: string }

defineProps<{
  form: { chapter_id: string; goal: string }
  batchRows: BatchRow[]
  batchSubmitting: boolean
  chapterPlanGenerating: boolean
  loading: boolean
}>()

const visible = defineModel<boolean>({ required: true })
const addChapterTab = defineModel<string>('addChapterTab', { required: true })
const batchInputMode = defineModel<string>('batchInputMode', { required: true })
const chapterPlanCount = defineModel<number>('chapterPlanCount', { required: true })
const chapterPlanInstructions = defineModel<string>('chapterPlanInstructions', { required: true })
const bulkText = defineModel<string>('bulkText', { required: true })

const emit = defineEmits<{
  submitChapter: []
  submitBatch: []
  fillBatchFromAI: []
  addBatchRow: []
  quickAddChapters: [count: number]
  clearBatchRows: []
  importFromBulkText: []
  removeBatchRow: [index: number]
}>()

const tasksStore = useTasksStore()
</script>

<template>
  <el-dialog v-model="visible" title="高级 · 补跑单章 / 列表" width="780px" top="6vh" destroy-on-close>
    <el-alert type="info" :closable="false" show-icon class="gen-mode-alert">
      <template #title>和「连写启动」的区别</template>
      <p class="gen-mode-text">
        <strong>连写启动</strong>（主按钮）：走卷队列 autopilot，长篇按卷滚动，适合连续写书。
        <strong>写作页 → AI 写作</strong>：边改边跑当前章流水线（常用）；会覆盖本章正文前会先提示。
        <strong>本对话框 · 单章</strong>：不打开写作页也可提交；<strong>列表</strong>：批量填 ID+目标，均不走全书规划。
      </p>
    </el-alert>
    <el-tabs v-model="addChapterTab" class="add-chapter-tabs">
      <el-tab-pane label="单章（不打开写作页）" name="single">
        <div class="run-form">
          <label>
            <span>章节编号</span>
            <el-input v-model="form.chapter_id" placeholder="001" style="width: 120px;" />
          </label>
          <label>
            <span>章节目标</span>
            <el-input
              v-model="form.goal"
              type="textarea"
              :rows="6"
              resize="none"
              placeholder="描述本章要推进的事件、冲突、伏笔或人物变化"
            />
          </label>
        </div>
        <div class="dialog-footer-actions">
          <el-button @click="visible = false">取消</el-button>
          <el-button
            type="primary"
            :loading="loading"
            :disabled="tasksStore.isRunning || loading"
            @click="emit('submitChapter')"
          >
            运行章节流水线
          </el-button>
        </div>
      </el-tab-pane>

      <el-tab-pane label="指定列表（无全书规划）" name="batch">
        <div class="batch-mode-selector">
          <el-radio-group v-model="batchInputMode" size="small">
            <el-radio-button value="list">列表录入</el-radio-button>
            <el-radio-button value="bulk">文本批量导入</el-radio-button>
          </el-radio-group>
        </div>

        <div v-if="batchInputMode === 'list'" class="list-mode-content">
          <div class="batch-toolbar">
            <div class="toolbar-left">
              <el-button
                type="primary"
                :loading="chapterPlanGenerating"
                :disabled="tasksStore.isRunning || chapterPlanGenerating"
                @click="emit('fillBatchFromAI')"
              >
                AI 根据大纲拆章
              </el-button>
              <el-button text :icon="Plus" :disabled="tasksStore.isRunning" @click="emit('addBatchRow')">
                添加一行
              </el-button>
              <el-button text :disabled="tasksStore.isRunning" @click="emit('quickAddChapters', 5)">
                + 快速加 5 章
              </el-button>
              <el-button text :disabled="tasksStore.isRunning" @click="emit('quickAddChapters', 10)">
                + 快速加 10 章
              </el-button>
            </div>
            <el-button text type="danger" :disabled="tasksStore.isRunning" @click="emit('clearBatchRows')">
              一键清空
            </el-button>
          </div>
          <div class="ai-plan-options">
            <span>生成</span>
            <el-input-number v-model="chapterPlanCount" :min="1" :max="200" size="small" />
            <span>章</span>
            <el-input
              v-model="chapterPlanInstructions"
              size="small"
              placeholder="可选：本轮拆章重点，例如先打进城市赛"
            />
          </div>

          <div class="batch-list">
            <div v-for="(row, index) in batchRows" :key="index" class="batch-row">
              <el-input v-model="row.chapter_id" placeholder="编号" class="batch-id" />
              <el-input v-model="row.goal" placeholder="章节目标描述" />
              <el-button
                text
                type="danger"
                :icon="Delete"
                :disabled="batchRows.length <= 1"
                @click="emit('removeBatchRow', index)"
              />
            </div>
          </div>
        </div>

        <div v-else class="bulk-mode-content">
          <p class="bulk-tip">请输入多个章节的目标描述，每一行代表一个章节：</p>
          <el-input
            v-model="bulkText"
            type="textarea"
            :rows="10"
            placeholder="例如：&#10;第一章：主角在雨夜回家的路上，遭遇了诡异车祸……&#10;第二章：在白塔医院醒来，却发现自己意外获得了透视眼……&#10;第三章：出院回家，遇到恶毒房东催租，发生冲突……"
            class="bulk-textarea"
          />
          <div class="bulk-actions">
            <el-button type="primary" @click="emit('importFromBulkText')">解析并导入到列表</el-button>
          </div>
        </div>

        <div class="dialog-footer-actions">
          <el-button @click="visible = false">取消</el-button>
          <el-button
            type="primary"
            :loading="batchSubmitting"
            :disabled="tasksStore.isRunning || batchSubmitting"
            @click="emit('submitBatch')"
          >
            提交批量任务 (共 {{ batchRows.filter((row) => row.chapter_id.trim() && row.goal.trim()).length }} 章)
          </el-button>
        </div>
      </el-tab-pane>
    </el-tabs>
  </el-dialog>
</template>

<style scoped>
.gen-mode-alert {
  margin-bottom: 14px;
}

.gen-mode-text {
  margin: 6px 0 0;
  font-size: 13px;
  line-height: 1.55;
  color: var(--color-text-muted);
}

.run-form {
  display: grid;
  gap: 14px;
  margin-top: 10px;
}

.run-form label {
  display: grid;
  gap: 6px;
}

.run-form span {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--color-text-muted);
}

.dialog-footer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

.batch-mode-selector {
  margin: 10px 0 16px;
  display: flex;
  justify-content: center;
}

.list-mode-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.batch-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--color-bg-surface-muted);
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid var(--color-border);
  margin-bottom: 8px;
}

.toolbar-left {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.ai-plan-options {
  display: grid;
  grid-template-columns: auto 120px auto minmax(220px, 1fr);
  align-items: center;
  gap: 8px;
  color: var(--color-text-muted);
  font-size: 13px;
}

.batch-list {
  margin-top: 14px;
  max-height: 380px;
  overflow-y: auto;
  display: grid;
  gap: 8px;
}

.batch-row {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr) 42px;
  gap: 8px;
  align-items: center;
}

.bulk-mode-content {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.bulk-tip {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-muted);
}

.bulk-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 10px;
}
</style>