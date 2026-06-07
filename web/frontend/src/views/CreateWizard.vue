<script setup lang="ts">
import { ArrowLeft } from '@element-plus/icons-vue'
import CreateModeTabs from '../components/create/CreateModeTabs.vue'
import CreateQuickPane from '../components/create/CreateQuickPane.vue'
import CreateParsePane from '../components/create/CreateParsePane.vue'
import CreateAiPane from '../components/create/CreateAiPane.vue'
import { useCreateWizard } from '../composables/useCreateWizard'

const {
  activeMode,
  quickFormRef,
  creating,
  aiModelReady,
  aiModelLabel,
  parseText,
  fileName,
  parseFileInput,
  analyzing,
  goBack,
  goToConfig,
  handleAiComplete,
  handleQuickCreate,
  triggerQuickSubmit,
  triggerFileSelect,
  handleParseFileUpload,
  handleAnalyzeSubmit,
} = useCreateWizard()
</script>

<template>
  <section class="create-page">
    <header class="create-header">
      <el-button text class="back-btn" @click="goBack">
        <el-icon><ArrowLeft /></el-icon>
        返回书库
      </el-button>
      <h1>新建作品</h1>
      <p>默认从快速创建开始；支持由 AI 进行对话引导或根据文字大纲内容解析建档。</p>
    </header>

    <CreateModeTabs
      v-model:active-mode="activeMode"
      :ai-model-ready="aiModelReady"
      :ai-model-label="aiModelLabel"
      @go-to-config="goToConfig"
    />

    <div class="mode-content">
      <CreateAiPane
        v-if="activeMode === 'ai'"
        :ai-model-ready="aiModelReady"
        :ai-model-label="aiModelLabel"
        @switch-to-quick="activeMode = 'quick'"
        @go-to-config="goToConfig"
        @ai-complete="handleAiComplete"
      />

      <CreateParsePane
        v-else-if="activeMode === 'parse'"
        v-model:parse-text="parseText"
        v-model:parse-file-input="parseFileInput"
        :analyzing="analyzing"
        :file-name="fileName"
        @go-back="goBack"
        @trigger-file-select="triggerFileSelect"
        @handle-parse-file-upload="handleParseFileUpload"
        @handle-analyze-submit="handleAnalyzeSubmit"
      />

      <CreateQuickPane
        v-else
        v-model:quick-form-ref="quickFormRef"
        :creating="creating"
        @go-back="goBack"
        @quick-create="handleQuickCreate"
        @trigger-submit="triggerQuickSubmit"
      />
    </div>
  </section>
</template>

<style scoped>
.create-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 32px 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.create-header {
  display: grid;
  gap: 4px;
}

.back-btn {
  justify-self: start;
  margin-bottom: 8px;
  color: #6b7280;
}

.create-header h1 {
  margin: 0;
  color: #111827;
  font-size: 28px;
  font-weight: 760;
}

.create-header p {
  margin: 0;
  color: #6b7280;
  font-size: 15px;
}

.mode-content {
  min-width: 0;
}
</style>