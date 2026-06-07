<script setup lang="ts">
import { Upload } from '@element-plus/icons-vue'

defineProps<{
  analyzing: boolean
  fileName: string
}>()

const parseText = defineModel<string>('parseText', { required: true })
const parseFileInput = defineModel<HTMLInputElement | null>('parseFileInput')

const emit = defineEmits<{
  goBack: []
  triggerFileSelect: []
  handleParseFileUpload: [event: Event]
  handleAnalyzeSubmit: []
}>()
</script>

<template>
  <div class="quick-wrapper">
    <div class="parse-container">
      <div class="parse-intro">
        <h3>粘贴文字或上传文件，让 AI 智能解析小说设定并一键建档</h3>
        <p>
          粘贴脑洞、大纲或素材，或上传 .md / .txt（Word 请先另存为 txt）。大模型将分析题材、拟定书名与主角，并生成世界观与读者承诺草案。
        </p>
      </div>

      <el-input
        v-model="parseText"
        type="textarea"
        :rows="12"
        placeholder="请在此粘贴您的小说脑洞、大纲、构想、角色卡或背景描述（越详尽分析越精准）..."
        class="parse-textarea"
      />

      <div class="parse-upload-row">
        <el-button type="warning" plain size="small" :icon="Upload" @click="emit('triggerFileSelect')">
          上传 Markdown/Txt 文件
        </el-button>
        <input
          :ref="(el) => { parseFileInput = el as HTMLInputElement | null }"
          type="file"
          accept=".md,.txt,.text"
          style="display: none"
          @change="emit('handleParseFileUpload', $event)"
        />
        <span v-if="fileName" class="uploaded-filename">
          已选择文件: <strong>{{ fileName }}</strong> (共 {{ parseText.length }} 字)
        </span>
      </div>
    </div>
    <div class="quick-footer">
      <el-button @click="emit('goBack')">取消</el-button>
      <el-button
        type="primary"
        :loading="analyzing"
        :disabled="!parseText.trim()"
        @click="emit('handleAnalyzeSubmit')"
      >
        开始分析并创建小说
      </el-button>
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

.parse-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.parse-intro h3 {
  margin: 0 0 6px;
  font-size: 16px;
  color: #111827;
}

.parse-intro p {
  margin: 0;
  font-size: 13.5px;
  color: #6b7280;
  line-height: 1.5;
}

.parse-textarea {
  font-family: inherit;
}

.parse-upload-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 4px;
}

.uploaded-filename {
  font-size: 13px;
  color: #374151;
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