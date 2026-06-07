<script setup lang="ts">
import { DataLine, Delete, MagicStick } from '@element-plus/icons-vue'
import type { TropeComponent, TropeSlotType } from '../../composables/useTropeWorkshop'

defineProps<{
  selectedChannel: TropeComponent | null
  selectedTheme: TropeComponent | null
  selectedMechanisms: TropeComponent[]
  selectedCoolPoints: TropeComponent[]
  isValidBlueprint: boolean
  guideLoading: boolean
  parsedGuideHtml: string
  currentProjectId?: string
  onRemoveFromBlueprint: (id: string, type: TropeSlotType) => void
  onDrop: (event: DragEvent, targetType: TropeSlotType) => void
  onOpenCreateDialog: () => void
  onApplyToActiveProject: () => void
}>()
</script>

<template>
  <main class="blueprint-workbench">
    <div class="workbench-header">
      <h3>套路组装工作台</h3>
      <div class="workbench-actions">
        <el-button
          type="success"
          :disabled="!isValidBlueprint"
          @click="onOpenCreateDialog"
          :icon="MagicStick"
        >
          以此新建作品
        </el-button>
        <el-button
          type="primary"
          :disabled="!isValidBlueprint || !currentProjectId"
          @click="onApplyToActiveProject"
          :icon="DataLine"
        >
          应用到当前作品
        </el-button>
      </div>
    </div>

    <div class="blueprint-slots">
      <div
        class="slot-wrapper"
        @dragover.prevent
        @drop="(e) => onDrop(e, 'channels')"
      >
        <label>主角定位 (Channel) <span class="req">*</span></label>
        <div v-if="selectedChannel" class="assembled-card chan-bg">
          <div class="assembled-info">
            <strong>{{ selectedChannel.name }}</strong>
            <span>{{ selectedChannel.description }}</span>
          </div>
          <el-button
            type="danger"
            :icon="Delete"
            circle
            size="small"
            @click="onRemoveFromBlueprint('', 'channels')"
          />
        </div>
        <div v-else class="empty-slot">
          拖拽或点击主角角色卡片到此处 (必选)
        </div>
      </div>

      <div
        class="slot-wrapper"
        @dragover.prevent
        @drop="(e) => onDrop(e, 'themes')"
      >
        <label>题材主题 (Theme) <span class="req">*</span></label>
        <div v-if="selectedTheme" class="assembled-card theme-bg">
          <div class="assembled-info">
            <strong>{{ selectedTheme.name }}</strong>
            <span>{{ selectedTheme.description }}</span>
          </div>
          <el-button
            type="danger"
            :icon="Delete"
            circle
            size="small"
            @click="onRemoveFromBlueprint('', 'themes')"
          />
        </div>
        <div v-else class="empty-slot">
          拖拽或点击题材主题卡片到此处 (必选)
        </div>
      </div>

      <div
        class="slot-wrapper"
        @dragover.prevent
        @drop="(e) => onDrop(e, 'mechanisms')"
      >
        <label>核心机制 (Mechanisms)</label>
        <div class="tags-container">
          <div
            v-for="item in selectedMechanisms"
            :key="item.id"
            class="assembled-card-small mech-bg"
          >
            <strong>{{ item.name }}</strong>
            <el-button
              type="danger"
              link
              :icon="Delete"
              @click="onRemoveFromBlueprint(item.id, 'mechanisms')"
            />
          </div>
          <div v-if="selectedMechanisms.length === 0" class="empty-slot-thin">
            暂无核心机制。支持放入多个机制
          </div>
        </div>
      </div>

      <div
        class="slot-wrapper"
        @dragover.prevent
        @drop="(e) => onDrop(e, 'cool_points')"
      >
        <label>爽点节奏 (Cool Points)</label>
        <div class="tags-container">
          <div
            v-for="item in selectedCoolPoints"
            :key="item.id"
            class="assembled-card-small cool-bg"
          >
            <strong>{{ item.name }}</strong>
            <el-button
              type="danger"
              link
              :icon="Delete"
              @click="onRemoveFromBlueprint(item.id, 'cool_points')"
            />
          </div>
          <div v-if="selectedCoolPoints.length === 0" class="empty-slot-thin">
            暂无爽点节奏。支持放入多个爽点
          </div>
        </div>
      </div>
    </div>

    <div class="preview-section" v-loading="guideLoading">
      <div class="preview-header">
        <h4>套路写作指南预览 (MD格式)</h4>
        <span v-if="!isValidBlueprint" class="validation-tip">配置完主角和题材题材后，系统将自动拼接生成</span>
      </div>

      <div class="preview-content">
        <div v-if="parsedGuideHtml" class="markdown-preview" v-html="parsedGuideHtml" />
        <el-empty v-else description="组装基本参数后，这里会展现系统为你拼接的设定指南" />
      </div>
    </div>
  </main>
</template>

<style scoped>
.blueprint-workbench {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
  max-height: calc(100vh - 120px);
  background: var(--color-bg-surface);
  border: 1px solid #e1e7ef;
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04);
}

.workbench-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--color-border-subtle);
  padding-bottom: 12px;
}

.workbench-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 750;
  color: #1a202c;
}

.workbench-actions {
  display: flex;
  gap: 10px;
}

.blueprint-slots {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  border-bottom: 1px solid var(--color-border-subtle);
  padding-bottom: 20px;
}

.slot-wrapper {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.slot-wrapper label {
  font-size: 13.5px;
  font-weight: 700;
  color: #4a5568;
}

.slot-wrapper label .req {
  color: var(--color-danger);
}

.assembled-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 12px;
  background: var(--color-bg-surface-muted);
}

.assembled-info {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.assembled-info strong {
  font-size: 14px;
  color: var(--color-text-strong);
}

.assembled-info span {
  font-size: 12px;
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chan-bg { border-left: 4px solid #0284c7; background: #f0f9ff; }
.theme-bg { border-left: 4px solid var(--color-success); background: #f0fdf4; }

.empty-slot {
  height: 60px;
  border: 2px dashed var(--color-border);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--color-text-subtle);
  background: var(--color-bg-surface-muted);
  text-align: center;
  padding: 0 10px;
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 10px;
  min-height: 60px;
  background: var(--color-bg-surface-muted);
  align-content: flex-start;
}

.assembled-card-small {
  display: flex;
  align-items: center;
  gap: 8px;
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 12.5px;
}

.mech-bg { background: #fef3c7; color: #b45309; border: 1px solid #fde68a; }
.cool-bg { background: #f3e8ff; color: #6b21a8; border: 1px solid #e9d5ff; }

.empty-slot-thin {
  font-size: 12px;
  color: var(--color-text-subtle);
  align-self: center;
  width: 100%;
  text-align: center;
}

.preview-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preview-header h4 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #2d3748;
}

.validation-tip {
  font-size: 11px;
  color: #e53e3e;
  background: #fff5f5;
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid #fed7d7;
}

.preview-content {
  flex: 1;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: #fafafa;
  min-height: 250px;
  padding: 16px;
  overflow-y: auto;
}

.markdown-preview {
  font-size: 14.5px;
  line-height: 1.6;
  color: #2d3748;
}

.markdown-preview h1 { font-size: 20px; border-bottom: 1px solid var(--color-border-subtle); padding-bottom: 8px; margin-top: 0; }
.markdown-preview h2 { font-size: 17px; margin-top: 18px; color: #1a202c; }
.markdown-preview h3 { font-size: 15px; margin-top: 14px; }
.markdown-preview p { margin: 8px 0; }
.markdown-preview ul { padding-left: 20px; margin: 8px 0; }
.markdown-preview li { margin: 4px 0; }
.markdown-preview hr { border: 0; border-top: 1px solid var(--color-border-subtle); margin: 16px 0; }
</style>