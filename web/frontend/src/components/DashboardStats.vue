<script setup lang="ts">
import { ref } from 'vue'
import { storeToRefs } from 'pinia'
import { CircleCheck, Clock, Document, Loading, Memo } from '@element-plus/icons-vue'
import { useChapterStore } from '../stores/chapter'
import RecentChapterDialog from './RecentChapterDialog.vue'

const store = useChapterStore()
const { chapters, completedTasks, runningTasks, totalWords } = storeToRefs(store)

const recentDialogVisible = ref(false)

function openRecentChapterDialog() {
  recentDialogVisible.value = true
}
</script>

<template>
  <div class="metric-grid">
    <button
      type="button"
      class="metric metric-clickable"
      aria-label="查看最近产出章节"
      @click="openRecentChapterDialog"
    >
      <span class="metric-icon m-orange"><el-icon><Document /></el-icon></span>
      <div>
        <div class="metric-label">已生成章节</div>
        <div class="metric-value">{{ chapters.length }}</div>
      </div>
    </button>
    <div class="metric">
      <span class="metric-icon m-blue"><el-icon><Memo /></el-icon></span>
      <div>
        <div class="metric-label">累计字数</div>
        <div class="metric-value">{{ totalWords.toLocaleString() }}</div>
      </div>
    </div>
    <div class="metric">
      <span class="metric-icon m-amber">
        <el-icon><Loading v-if="runningTasks" class="is-loading" /><Clock v-else /></el-icon>
      </span>
      <div>
        <div class="metric-label">进行中任务</div>
        <div class="metric-value">{{ runningTasks }}</div>
      </div>
    </div>
    <div class="metric">
      <span class="metric-icon m-green"><el-icon><CircleCheck /></el-icon></span>
      <div>
        <div class="metric-label">已完成任务</div>
        <div class="metric-value">{{ completedTasks }}</div>
      </div>
    </div>
  </div>

  <RecentChapterDialog v-model:visible="recentDialogVisible" />
</template>

<style scoped>
.metric {
  display: flex;
  align-items: center;
  gap: 14px;
}

.metric-clickable {
  width: 100%;
  font: inherit;
  color: inherit;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.15s ease;
}

.metric-clickable:hover {
  border-color: rgba(198, 111, 79, 0.35);
  box-shadow: 0 6px 18px -10px rgba(198, 111, 79, 0.35);
}

.metric-clickable:active {
  transform: translateY(1px);
}

.metric-clickable:focus-visible {
  outline: 2px solid rgba(198, 111, 79, 0.45);
  outline-offset: 2px;
}

.metric-icon {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 8px;
  font-size: 20px;
}

.m-orange { background: #fff1ea; color: #c66f4f; }
.m-blue { background: #eaf6fc; color: #2f6f90; }
.m-amber { background: #fff8df; color: #d49528; }
.m-green { background: #eaf8f0; color: #3ea66d; }
</style>