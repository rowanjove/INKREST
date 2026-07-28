<script setup lang="ts">
import { View } from '@element-plus/icons-vue'
import CharacterAssetEditor from '../CharacterAssetEditor.vue'
import RulesAssetEditor from '../RulesAssetEditor.vue'
import MarkdownAssetEditor from '../MarkdownAssetEditor.vue'
import SensitiveWordsConfig from '../SensitiveWordsConfig.vue'
import type { AssetMeta } from '../../utils/assetEditorConfig'

defineProps<{
  loading: boolean
  saving: boolean
  currentAsset: { name: string; label?: string; path: string; content: string } | null
  currentTitle: string
  currentMeta: AssetMeta | null
  supportsAssetSource: boolean
  isMarkdownAsset: boolean
  contentBlocks: string[]
}>()

const editContent = defineModel<string>('editContent', { required: true })
const showAssetSource = defineModel<boolean>('showAssetSource', { required: true })

defineEmits<{
  save: []
  'open-add-term': []
}>()
</script>

<template>
  <main class="editor-panel" v-loading="loading">
    <div class="editor-toolbar">
      <div class="asset-title">
        <span v-if="currentMeta" class="asset-title-icon" :class="currentMeta.tone">
          <el-icon><component :is="currentMeta.icon" /></el-icon>
        </span>
        <div>
          <h2>{{ currentTitle }}</h2>
          <p v-if="currentAsset">{{ currentMeta?.description }} · {{ currentAsset.path }}</p>
        </div>
      </div>
      <div style="display: flex; gap: 10px;">
        <el-button
          v-if="currentAsset && currentAsset.name === 'terminology'"
          type="warning"
          :disabled="saving"
          @click="$emit('open-add-term')"
        >
          ➕ 新增名词
        </el-button>
        <el-button type="primary" :loading="saving" :disabled="!currentAsset" @click="$emit('save')">
          保存
        </el-button>
        <el-button
          v-if="supportsAssetSource"
          :icon="View"
          :type="showAssetSource ? 'warning' : 'default'"
          :disabled="!currentAsset"
          @click="showAssetSource = !showAssetSource"
        >
          {{ showAssetSource ? '隐藏源码' : '查看源码' }}
        </el-button>
      </div>
    </div>

    <div v-if="currentAsset" class="editor-workspace-container">
      <CharacterAssetEditor
        v-if="currentAsset.name === 'character_cards'"
        v-model="editContent"
        :show-source="showAssetSource"
        @save="$emit('save')"
      />

      <RulesAssetEditor
        v-else-if="currentAsset.name === 'rules'"
        v-model="editContent"
        @save="$emit('save')"
      />

      <SensitiveWordsConfig
        v-else-if="currentAsset.name === 'sensitive_words'"
        v-model="editContent"
      />

      <MarkdownAssetEditor
        v-else-if="isMarkdownAsset"
        v-model="editContent"
        :title="currentTitle"
        :path="currentAsset.path"
        :show-source="showAssetSource"
        @save="$emit('save')"
      />

      <div v-else class="asset-workspace">
        <aside class="asset-inspector">
          <div class="inspector-card">
            <span>类型</span>
            <strong>{{ currentMeta?.group }}</strong>
          </div>
          <div class="inspector-card">
            <span>状态</span>
            <strong>{{ editContent.trim() ? '已创建' : '未填写' }}</strong>
          </div>
          <div class="inspector-card">
            <span>内容索引</span>
            <div v-if="contentBlocks.length" class="block-list">
              <button v-for="block in contentBlocks" :key="block" type="button">{{ block }}</button>
            </div>
            <small v-else>暂无可识别条目</small>
          </div>
        </aside>
        <el-input
          v-model="editContent"
          type="textarea"
          resize="none"
          class="asset-textarea"
          spellcheck="false"
        />
      </div>
    </div>
    <el-empty v-else description="暂无资产文件" />
  </main>
</template>

<style scoped>
.editor-panel {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  overflow: hidden;
  background: var(--color-bg-surface);
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
}

.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
  border-bottom: 1px solid var(--color-border-subtle);
}

.asset-title {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.asset-title-icon {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  flex: none;
  border-radius: 8px;
}

.asset-title-icon.blue { background: #eef6fb; color: #2f6f90; }
.asset-title-icon.green { background: #ecfdf5; color: #15803d; }
.asset-title-icon.purple { background: #f5f3ff; color: #6d4cc2; }
.asset-title-icon.orange { background: #fff4ee; color: #b65f3e; }
.asset-title-icon.gray { background: var(--color-bg-hover); color: var(--color-text-muted); }

.editor-toolbar h2 {
  margin: 0;
  font-size: 18px;
  color: var(--color-text-strong);
}

.editor-toolbar p {
  margin: 4px 0 0;
  color: #7b8494;
  font-size: 13px;
}

.editor-workspace-container {
  min-height: 0;
  height: 100%;
}

.asset-workspace {
  min-height: 0;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  height: 100%;
}

.asset-inspector {
  display: grid;
  align-content: start;
  gap: 10px;
  padding: 14px;
  border-right: 1px solid var(--color-border-subtle);
  background: #fbfcfe;
}

.inspector-card {
  display: grid;
  gap: 6px;
  padding: 12px;
  border: 1px solid #e5eaf2;
  border-radius: 8px;
  background: var(--color-bg-surface);
}

.inspector-card span {
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 800;
}

.inspector-card strong {
  color: #111827;
  font-size: 14px;
}

.inspector-card small {
  color: var(--color-text-subtle);
}

.block-list {
  display: grid;
  gap: 6px;
}

.block-list button {
  overflow: hidden;
  padding: 6px 8px;
  border: 1px solid #e5eaf2;
  border-radius: 7px;
  background: var(--color-bg-surface-muted);
  color: var(--color-text-muted);
  text-align: left;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.asset-textarea {
  height: 100%;
}

.asset-textarea :deep(.el-textarea__inner) {
  height: 100%;
  min-height: 420px !important;
  border: 0;
  border-radius: 0;
  box-shadow: none;
  padding: 18px;
  font-family: "Cascadia Mono", Consolas, monospace;
  font-size: 14px;
  line-height: 1.7;
}
</style>