<script setup lang="ts">
import { ref, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { storeToRefs } from 'pinia'
import { Delete, Bottom } from '@element-plus/icons-vue'
import { useTasksStore } from '../stores/tasks'

const tasksStore = useTasksStore()
const { logs } = storeToRefs(tasksStore)
const logContainer = ref<HTMLElement | null>(null)
/** 跟随最新：默认开启，新日志自动滚到底；关闭后便于复制历史 */
const followTail = ref(true)
const SCROLL_BOTTOM_THRESHOLD = 48

const levelColors: Record<string, string> = {
  info: '#52c41a',
  warn: '#e6a23c',
  error: '#f56c6c',
  debug: '#909399',
}

const formatTime = (ts: number) => {
  const d = new Date(ts)
  return d.toLocaleTimeString('zh-CN', { hour12: false })
}

const stepLabels: Record<string, string> = {
  init: '初始化',
  planner: '规划',
  writer: '写作',
  merge: '合并',
  stitch_editor: '接缝修复',
  style_editor: '文风优化',
  continuity_checker: '连续性检查',
  chapter_summary: '章节总结',
  auditor: '审校',
  sensitive_scan: '敏感词扫描',
  state_update: '状态同步',
  vector_index: '向量索引',
  complete: '完成',
  error: '错误',
  ensure_queue: '同步卷队列',
  managing_editor: '主编拆卷',
}

const isNearBottom = (el: HTMLElement) =>
  el.scrollHeight - el.scrollTop - el.clientHeight <= SCROLL_BOTTOM_THRESHOLD

const scrollToBottom = (behavior: ScrollBehavior = 'auto', force = false) => {
  const el = logContainer.value
  if (!el) return
  if (!force && !followTail.value) return
  el.scrollTo({ top: el.scrollHeight, behavior })
}

const onLogScroll = () => {
  const el = logContainer.value
  if (!el) return
  if (!isNearBottom(el)) {
    followTail.value = false
  }
}

const jumpToBottom = () => {
  nextTick(() => scrollToBottom('smooth', true))
}

watch(followTail, (on) => {
  if (on) nextTick(() => scrollToBottom('auto', true))
})

watch(
  () => logs.value.length,
  async () => {
    if (!followTail.value) return
    await nextTick()
    scrollToBottom()
  },
)

const handleClear = async () => {
  await tasksStore.clearLogs()
  if (followTail.value) {
    nextTick(() => scrollToBottom('auto', true))
  }
}

onMounted(() => {
  tasksStore.startRuntimeLogPolling()
})

onBeforeUnmount(() => {
  tasksStore.stopRuntimeLogPolling()
})
</script>

<template>
  <div class="log-stream">
    <div class="log-header">
      <h3>Agent 实时日志</h3>
      <div class="log-controls">
        <div class="follow-group">
          <el-switch v-model="followTail" size="small" />
          <span class="follow-label">自动跟随</span>
          <el-button text size="small" :icon="Bottom" @click="jumpToBottom">
            跳到底部
          </el-button>
        </div>
        <el-button text size="small" @click="handleClear">
          <el-icon><Delete /></el-icon> 清空
        </el-button>
      </div>
    </div>
    <div
      ref="logContainer"
      class="log-body"
      @scroll="onLogScroll"
    >
      <div v-if="logs.length === 0" class="log-empty">
        等待日志输出…
      </div>
      <div
        v-for="(entry, idx) in logs"
        :key="`${entry.timestamp}-${entry.step}-${idx}`"
        class="log-line"
      >
        <span class="log-time">{{ formatTime(entry.timestamp) }}</span>
        <span class="log-level" :style="{ color: levelColors[entry.level] || '#909399' }">
          [{{ entry.level.toUpperCase() }}]
        </span>
        <span v-if="entry.step" class="log-step">{{ stepLabels[entry.step] || entry.step }}</span>
        <span class="log-msg">{{ entry.message }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.log-stream {
  display: flex;
  flex-direction: column;
  height: 100%;
  max-height: 100%;
  min-height: 0;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: #1a1d23;
  overflow: hidden;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
  padding: 12px 16px;
  background: #22262e;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.log-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #e0e4ea;
}

.log-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.follow-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.follow-label {
  font-size: 12px;
  color: #a8b0bc;
  white-space: nowrap;
  user-select: none;
}

.log-controls .el-button {
  color: #909399;
  font-size: 12px;
}

.log-body {
  flex: 1;
  min-height: 0;
  max-height: 100%;
  padding: 12px 16px;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  font-family: ui-monospace, Consolas, 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.65;
  user-select: text;
  -webkit-user-select: text;
}

.log-empty {
  color: #555;
  font-style: italic;
  text-align: center;
  padding: 40px;
}

.log-line {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: baseline;
  padding: 1px 0;
}

.log-time {
  color: #555;
  flex-shrink: 0;
}

.log-level {
  flex-shrink: 0;
  font-weight: 600;
  min-width: 48px;
}

.log-step {
  color: #7eb8da;
  flex-shrink: 0;
}

.log-msg {
  color: #c8cdd5;
  flex: 1;
  min-width: 0;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>