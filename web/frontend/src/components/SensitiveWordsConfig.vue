<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  modelValue: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const wordCount = computed(() =>
  props.modelValue
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith('#')).length,
)
</script>

<template>
  <div class="sensitive-words-editor">
    <div class="editor-info-bar">
      <span>已配置 {{ wordCount }} 条敏感词（审校硬扫描）</span>
      <p class="hint">
        文件路径：<code>assets/sensitive_words.txt</code>。每行一词，<code>#</code> 开头为注释。
        章节审校与敏感词报告会读取本库；<strong>与写作规则里的「禁用词」不同</strong>——禁用词主要约束模型措辞，此处用于合规/平台红线拦截。
        剧情设定库中的「敏感词过滤」编辑的是同一文件，以本页保存为准。
      </p>
    </div>

    <div class="editor-body-wrap">
      <el-input
        :model-value="props.modelValue"
        type="textarea"
        :rows="18"
        resize="vertical"
        spellcheck="false"
        placeholder="# 示例（可删）&#10;违禁词甲&#10;违禁词乙"
        @input="(val: string) => emit('update:modelValue', val)"
      />
    </div>
  </div>
</template>

<style scoped>
.sensitive-words-editor {
  display: grid;
  gap: 16px;
  width: 100%;
}

.editor-info-bar {
  background: var(--color-bg-surface-muted);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 14px 18px;
}

.editor-info-bar span {
  font-weight: 750;
  color: var(--color-text-strong);
  font-size: 15px;
  display: block;
}

.hint {
  margin: 6px 0 0;
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 1.55;
}

.hint code {
  font-size: 12px;
}

.editor-body-wrap :deep(.el-textarea__inner) {
  font-family: "Cascadia Mono", Consolas, monospace;
  line-height: 1.7;
  font-size: 14px;
}
</style>