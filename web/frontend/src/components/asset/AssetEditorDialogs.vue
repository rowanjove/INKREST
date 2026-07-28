<script setup lang="ts">
import { assetTypeOptions, type AssetTypeKey } from '../../utils/assetEditorConfig'

defineProps<{
  creating: boolean
  generating: boolean
  selectedAssetType: (typeof assetTypeOptions)[number]
  onCreate: () => void
  onGenerate: () => void
  onAddTerm: () => void
}>()

const createDialogVisible = defineModel<boolean>('createDialogVisible', { required: true })
const generateDialogVisible = defineModel<boolean>('generateDialogVisible', { required: true })
const addTermDialogOpen = defineModel<boolean>('addTermDialogOpen', { required: true })

const createForm = defineModel<{
  name: string
  label: string
  extension: string
  content: string
}>('createForm', { required: true })

const generateForm = defineModel<{
  name: string
  label: string
  assetTypeKey: AssetTypeKey
  count: number
  attributesText: string
  parameters: Record<string, string>
  instructions: string
}>('generateForm', { required: true })

const addTermForm = defineModel<{
  name: string
  description: string
}>('addTermForm', { required: true })
</script>

<template>
  <el-dialog v-model="createDialogVisible" title="新增资产" width="520px">
    <el-form label-width="100px">
      <el-form-item label="资产标识" required><el-input v-model="createForm.name" placeholder="如 villain_cards" /></el-form-item>
      <el-form-item label="显示名称"><el-input v-model="createForm.label" placeholder="如 反派角色卡" /></el-form-item>
      <el-form-item label="文件类型">
        <el-select v-model="createForm.extension">
          <el-option label="Markdown" value="md" />
          <el-option label="YAML" value="yaml" />
          <el-option label="JSON" value="json" />
          <el-option label="Text" value="txt" />
        </el-select>
      </el-form-item>
      <el-form-item label="初始内容"><el-input v-model="createForm.content" type="textarea" :rows="6" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="createDialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="creating" @click="onCreate">创建</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="generateDialogVisible" title="AI 生成资产" width="680px">
    <el-form label-width="110px">
      <el-form-item label="保存标识" required><el-input v-model="generateForm.name" /></el-form-item>
      <el-form-item label="显示名称"><el-input v-model="generateForm.label" /></el-form-item>
      <el-form-item label="素材类型">
        <el-select v-model="generateForm.assetTypeKey" class="full-select">
          <el-option
            v-for="option in assetTypeOptions"
            :key="option.key"
            :label="option.label"
            :value="option.key"
          />
        </el-select>
      </el-form-item>
      <div class="type-helper">{{ selectedAssetType.helper }}</div>

      <div class="type-panel">
        <template v-if="generateForm.assetTypeKey === 'character_cards'">
          <el-form-item label="角色数量"><el-input-number v-model="generateForm.count" :min="1" :max="50" /></el-form-item>
          <el-form-item label="角色属性"><el-input v-model="generateForm.attributesText" /></el-form-item>
        </template>
        <template v-else-if="generateForm.assetTypeKey === 'world_bible'">
          <el-form-item label="设定模块"><el-input v-model="generateForm.attributesText" /></el-form-item>
          <el-form-item label="模块数量"><el-input-number v-model="generateForm.count" :min="1" :max="20" /></el-form-item>
        </template>
        <template v-else-if="generateForm.assetTypeKey === 'style_guide'">
          <el-form-item label="指南维度"><el-input v-model="generateForm.attributesText" /></el-form-item>
          <el-form-item label="示例数量"><el-input-number v-model="generateForm.count" :min="1" :max="20" /></el-form-item>
        </template>
        <template v-else-if="generateForm.assetTypeKey === 'rules'">
          <el-form-item label="规则维度"><el-input v-model="generateForm.attributesText" /></el-form-item>
          <el-form-item label="规则组数"><el-input-number v-model="generateForm.count" :min="1" :max="20" /></el-form-item>
        </template>
        <template v-else>
          <el-form-item label="素材数量"><el-input-number v-model="generateForm.count" :min="1" :max="50" /></el-form-item>
          <el-form-item label="素材属性"><el-input v-model="generateForm.attributesText" /></el-form-item>
        </template>

        <div class="parameter-grid">
          <label v-for="(_, key) in generateForm.parameters" :key="key" class="parameter-field">
            <span>{{ key }}</span>
            <el-input v-model="generateForm.parameters[key]" />
          </label>
        </div>
      </div>
      <el-form-item label="额外要求"><el-input v-model="generateForm.instructions" type="textarea" :rows="4" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="generateDialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="generating" @click="onGenerate">生成并保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="addTermDialogOpen" title="新增专有名词解释" width="500px" top="15vh" destroy-on-close>
    <el-form label-width="80px">
      <el-form-item label="名词" required>
        <el-input v-model="addTermForm.name" placeholder="请输入你要新增的专业术语或名词" />
      </el-form-item>
      <el-form-item label="解释说明" required>
        <el-input
          v-model="addTermForm.description"
          type="textarea"
          :rows="4"
          placeholder="请输入对该名词的详细解释"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="addTermDialogOpen = false">取消</el-button>
      <el-button type="primary" @click="onAddTerm">确定并追加</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.full-select {
  width: 100%;
}

.type-helper {
  margin: -8px 0 14px 110px;
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 1.5;
}

.type-panel {
  margin: 0 0 18px 110px;
  padding: 12px 14px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: var(--color-bg-surface-muted);
}

.type-panel :deep(.el-form-item) {
  margin-bottom: 12px;
}

.parameter-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.parameter-field {
  display: grid;
  gap: 6px;
}

.parameter-field span {
  color: #526075;
  font-size: 12px;
  font-weight: 650;
}

@media (max-width: 980px) {
  .type-helper,
  .type-panel {
    margin-left: 0;
  }

  .parameter-grid {
    grid-template-columns: 1fr;
  }
}
</style>