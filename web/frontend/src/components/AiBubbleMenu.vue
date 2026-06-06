<script setup lang="ts">
import { ref } from 'vue'
import { inlineRewrite } from '../api'
import { ElMessage } from 'element-plus'

const props = defineProps<{
  visible: boolean
  x: number
  y: number
  selectedText: string
  chapterId: string
  chapterGoal: string
}>()

const emit = defineEmits<{
  (e: 'accept', text: string): void
  (e: 'close'): void
  (e: 'expand'): void
}>()

const loading = ref(false)
const customInstruction = ref('')
const showCustomInput = ref(false)
const rewrittenText = ref('')
const showResult = ref(false)

const handlePresetRewrite = async (instruction: string) => {
  if (!props.selectedText.trim()) return
  loading.value = true
  rewrittenText.value = ''
  showResult.value = false
  
  try {
    const { data } = await inlineRewrite({
      text: props.selectedText,
      instruction,
      chapter_id: props.chapterId,
      goal: props.chapterGoal
    })
    rewrittenText.value = data.rewritten_text
    showResult.value = true
  } catch (e: any) {
    ElMessage.error('AI 改写失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

const handleCustomRewrite = () => {
  if (!customInstruction.value.trim()) return
  handlePresetRewrite(customInstruction.value.trim())
}

const handleAccept = () => {
  if (rewrittenText.value) {
    emit('accept', rewrittenText.value)
    handleClose()
  }
}

const handleClose = () => {
  customInstruction.value = ''
  showCustomInput.value = false
  rewrittenText.value = ''
  showResult.value = false
  loading.value = false
  emit('close')
}
</script>

<template>
  <div
    v-if="visible"
    class="ai-bubble-menu"
    :style="{ top: y + 'px', left: x + 'px' }"
    @mousedown.stop
  >
    <!-- 原始修改选项 -->
    <div v-if="!loading && !showResult" class="bubble-actions-row">
      <button class="action-btn" @click="emit('expand')">✍️ 续写</button>
      <button class="action-btn" @click="handlePresetRewrite('润色当前文本，让文笔更加细腻生动，修饰词藻。')">✨ 润色</button>
      <button class="action-btn" @click="handlePresetRewrite('将改写文本风格变为更加热血、激昂、充满张力。')">🔥 热血</button>
      <button class="action-btn" @click="handlePresetRewrite('将改写文本风格变为更加凄凉、悲壮、触动人心。')">😢 凄凉</button>
      <button class="action-btn" @click="handlePresetRewrite('将改写文本进行风趣幽默化改造，加入适度玩梗或调侃。')">😄 幽默</button>
      <button class="action-btn" @click="showCustomInput = !showCustomInput">✏️ 自定义</button>
      <button class="action-btn close-x" @click="handleClose">×</button>
    </div>

    <!-- 自定义指令输入框 -->
    <div v-if="showCustomInput && !loading && !showResult" class="custom-input-row">
      <el-input
        v-model="customInstruction"
        placeholder="输入修改指令（如：扩写环境描写）"
        size="small"
        @keydown.enter="handleCustomRewrite"
      >
        <template #append>
          <el-button type="primary" size="small" @click="handleCustomRewrite">发送</el-button>
        </template>
      </el-input>
    </div>

    <!-- Loading 状态 -->
    <div v-if="loading" class="loading-state">
      <span class="loading-spinner">🔄</span> AI 正在努力改写中...
    </div>

    <!-- 结果展示与比对 -->
    <div v-if="showResult" class="result-compare-panel">
      <div class="compare-columns">
        <div class="compare-col original">
          <div class="col-header">原文</div>
          <div class="col-text">{{ selectedText }}</div>
        </div>
        <div class="compare-col target">
          <div class="col-header">改写后</div>
          <div class="col-text">{{ rewrittenText }}</div>
        </div>
      </div>
      <div class="result-actions">
        <el-button size="small" @click="showResult = false">返回修改</el-button>
        <el-button size="small" type="primary" @click="handleAccept">替换采纳</el-button>
        <el-button size="small" type="danger" plain @click="handleClose">放弃</el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ai-bubble-menu {
  position: absolute;
  z-index: 2000;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid rgba(220, 227, 237, 0.6);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(10, 24, 48, 0.12), 0 2px 6px rgba(10, 24, 48, 0.04);
  padding: 6px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  transform: translate(-50%, -100%) translateY(-8px); /* 居中定位在选中文本上方 */
  min-width: 200px;
  max-width: 480px;
}

.bubble-actions-row {
  display: flex;
  align-items: center;
  gap: 4px;
}

.action-btn {
  background: transparent;
  border: 0;
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 12px;
  font-weight: 500;
  color: #4a5568;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}

.action-btn:hover {
  background: var(--color-bg-hover);
  color: #007aff;
}

.action-btn.close-x {
  font-size: 14px;
  color: #a0aec0;
  padding: 4px 6px;
}

.action-btn.close-x:hover {
  color: #e53e3e;
  background: rgba(229, 62, 62, 0.08);
}

.custom-input-row {
  padding: 2px 4px;
}

.loading-state {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #4a5568;
  padding: 8px 12px;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.loading-spinner {
  display: inline-block;
  animation: spin 1.2s infinite linear;
}

/* ---- Compare View ---- */
.result-compare-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 4px;
}

.compare-columns {
  display: flex;
  gap: 8px;
  border-bottom: 1px solid var(--color-border-subtle);
  padding-bottom: 8px;
}

.compare-col {
  flex: 1;
  min-width: 160px;
  max-height: 180px;
  overflow-y: auto;
  padding: 6px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.45;
}

.compare-col.original {
  background: #f7fafc;
  border: 1px dashed var(--color-border);
  color: #718096;
}

.compare-col.target {
  background: #f0fff4;
  border: 1px dashed #c6f6d5;
  color: #22543d;
  font-weight: 500;
}

.col-header {
  font-size: 11px;
  font-weight: bold;
  margin-bottom: 4px;
  color: #a0aec0;
}

.result-actions {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
}
</style>
