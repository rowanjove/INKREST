<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getConfig, listModels, updateConfig } from '../api'

const config = ref<any>({})
const libraryModels = ref<any[]>([])
const expanded = ref(false)
const savingTiers = ref(false)
const overrideDialogVisible = ref(false)
const editingRole = ref('')
const overrideModelRef = ref('')

const agentRoles = [
  { key: 'novel_chat', label: 'AI 创作引导', tier: 'daily' },
  { key: 'chief_editor', label: '总编 Agent', tier: 'reasoning' },
  { key: 'managing_editor', label: '主编 Agent', tier: 'reasoning' },
  { key: 'chapter_planner', label: '大纲编剧 Agent', tier: 'reasoning' },
  { key: 'planner', label: '章节规划 Agent', tier: 'reasoning' },
  { key: 'writer', label: '正文写手 Agent', tier: 'daily' },
  { key: 'stitch_editor', label: '拼接润色 Agent', tier: 'daily' },
  { key: 'style_editor', label: '文风润色 Agent', tier: 'daily' },
  { key: 'length_fix', label: '长度修正 Agent', tier: 'daily' },
  { key: 'auditor', label: '审核 QA Agent', tier: 'reasoning' },
  { key: 'chapter_summary', label: '章节总结 Agent', tier: 'daily' },
  { key: 'continuity_checker', label: '连续性检查 Agent', tier: 'reasoning' },
  { key: 'state_extractor', label: '状态提取 Agent', tier: 'reasoning' },
  { key: 'asset_compressor', label: '素材压缩 Agent', tier: 'daily' },
  { key: 'persona_reader', label: '角色阅读 Agent', tier: 'daily' },
  { key: 'asset_generator', label: '素材生成 Agent', tier: 'daily' },
  { key: 'compressor', label: '压缩 Agent', tier: 'daily' },
  { key: 'expander', label: '扩写 Agent', tier: 'daily' },
]

const loadConfig = async () => {
  const { data } = await getConfig()
  config.value = data
}

const loadModels = async () => {
  try {
    const { data } = await listModels()
    libraryModels.value = data.filter((model: any) => !model.type || model.type === 'text')
  } catch {
    libraryModels.value = []
  }
}

const ensureLlmConfig = () => {
  if (!config.value.llm) config.value.llm = {}
  return config.value.llm
}

const dailyModelId = computed(
  () => config.value.llm?.daily_model_id || config.value.llm?.default_model_id || config.value.llm?.default?.model_ref || '',
)

const reasoningModelId = computed(
  () => config.value.llm?.reasoning_model_id || dailyModelId.value,
)

const dailySlotLabel = computed(() => {
  const m = libraryModels.value.find((item: any) => item.id === dailyModelId.value)
  return m ? `${m.name || m.id} (${m.model})` : dailyModelId.value ? `未在模型库 (${dailyModelId.value})` : '未设置 — 请到模型库选择日常档'
})

const reasoningSlotLabel = computed(() => {
  const m = libraryModels.value.find((item: any) => item.id === reasoningModelId.value)
  return m ? `${m.name || m.id} (${m.model})` : reasoningModelId.value ? `未在模型库 (${reasoningModelId.value})` : '未设置 — 请到模型库选择逻辑档'
})

const backupSlotLabel = computed(() => {
  const ids: string[] = config.value.llm?.fallback_model_ids || []
  if (!ids.length) return '无'
  return ids
    .map((id) => {
      const m = libraryModels.value.find((item: any) => item.id === id)
      return m ? m.name || m.id : id
    })
    .join(' → ')
})

const routeCount = computed(() => Object.keys(config.value.llm?.overrides || {}).length)

const modelLabel = (modelId: string) => {
  const model = libraryModels.value.find((item: any) => item.id === modelId)
  return model ? `${model.name || model.id} (${model.model})` : `未在模型库中配置 (${modelId})`
}

const getTier = (row: any) => config.value.llm?.role_tiers?.[row.key] || row.tier
const getTierLabel = (row: any) => getTier(row) === 'reasoning' ? '逻辑档' : '日常档'
const getTierModelId = (row: any) => getTier(row) === 'reasoning' ? reasoningModelId.value : dailyModelId.value
const getOverride = (roleKey: string) => config.value.llm?.overrides?.[roleKey]
const getOverrideModelRef = (roleKey: string) => getOverride(roleKey)?.model_ref || ''

const saveTiers = async () => {
  savingTiers.value = true
  try {
    const llm = ensureLlmConfig()
    llm.role_tiers = Object.fromEntries(agentRoles.map(row => [row.key, getTier(row)]))
    await updateConfig({ llm: ensureLlmConfig() })
    ElMessage.success('Agent 档位映射已保存')
    await loadConfig()
  } catch (error: any) {
    ElMessage.error(error.message || '保存失败')
  } finally {
    savingTiers.value = false
  }
}

const openOverrideDialog = (roleKey: string) => {
  editingRole.value = roleKey
  overrideModelRef.value = getOverrideModelRef(roleKey)
  overrideDialogVisible.value = true
}

const saveOverride = async () => {
  try {
    const llm = ensureLlmConfig()
    if (!llm.overrides) llm.overrides = {}
    if (overrideModelRef.value) {
      llm.overrides[editingRole.value] = { model_ref: overrideModelRef.value }
    } else {
      delete llm.overrides[editingRole.value]
    }
    await updateConfig({ llm: ensureLlmConfig() })
    ElMessage.success('模型路由已保存（全局生效）')
    overrideDialogVisible.value = false
    await loadConfig()
  } catch (error: any) {
    ElMessage.error(error.message || '保存失败')
  }
}

const removeOverride = async (roleKey: string) => {
  try {
    if (config.value.llm?.overrides) {
      delete config.value.llm.overrides[roleKey]
      await updateConfig({ llm: config.value.llm })
      ElMessage.success('已恢复档位继承')
      await loadConfig()
    }
  } catch (error: any) {
    ElMessage.error(error.message || '移除失败')
  }
}

onMounted(async () => {
  await Promise.all([loadConfig(), loadModels()])
})
defineExpose({ loadConfig, loadModels })
</script>

<template>
  <section class="fold-card">
    <div class="fold-head" @click="expanded = !expanded">
      <div class="head-left">
        <span class="collapse-arrow" :class="{ open: expanded }">▶</span>
        <div>
          <h2>Agent 文本模型路由</h2>
          <p>日常档处理高频写作，逻辑档处理规划与校验；已单独路由 {{ routeCount }} 个 Agent。</p>
        </div>
      </div>
      <el-button class="fold-action" size="small" type="primary" @click.stop="expanded = !expanded">
        {{ expanded ? '收起' : '编辑配置' }}
      </el-button>
    </div>

    <div v-show="expanded" class="fold-body">
      <div class="tier-grid tier-grid-readonly">
        <div class="tier-card">
          <strong>日常档</strong>
          <span>正文、润色、摘要等高频任务</span>
          <p class="tier-model-line">{{ dailySlotLabel }}</p>
        </div>
        <div class="tier-card reasoning">
          <strong>逻辑档</strong>
          <span>规划、审核、连续性与状态提取</span>
          <p class="tier-model-line">{{ reasoningSlotLabel }}</p>
        </div>
        <div class="tier-card backup">
          <strong>备用</strong>
          <span>主模型失败时按顺序 fallback</span>
          <p class="tier-model-line">{{ backupSlotLabel }}</p>
        </div>
      </div>
      <p class="hint tier-hint">日常档 / 逻辑档 / 备用请在上方 <strong>模型库</strong> 每张卡片或编辑弹窗里设置；此处仅展示当前全局档位。</p>
      <div class="tier-actions">
        <el-button type="primary" :loading="savingTiers" @click="saveTiers">保存 Agent 档位映射</el-button>
      </div>

      <p class="hint">每个 Agent 默认继承所属档位；确有需要时，可继续为单个 Agent 指定独立模型。</p>
      <el-table :data="agentRoles" size="small" stripe>
        <el-table-column prop="label" label="角色" width="180" />
        <el-table-column prop="key" label="标识" width="170" />
        <el-table-column label="继承档位" width="100">
          <template #default="{ row }">
            <el-tag :type="getTier(row) === 'reasoning' ? 'warning' : 'info'" size="small">{{ getTierLabel(row) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="当前模型">
          <template #default="{ row }">
            <span v-if="getOverrideModelRef(row.key)">{{ modelLabel(getOverrideModelRef(row.key)) }}</span>
            <span v-else-if="getTierModelId(row)" class="muted">继承{{ getTierLabel(row) }}：{{ modelLabel(getTierModelId(row)) }}</span>
            <span v-else class="muted">未配置</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="getOverride(row.key) ? 'success' : 'info'" size="small">
              {{ getOverride(row.key) ? '单独路由' : '档位继承' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="openOverrideDialog(row.key)">编辑</el-button>
            <el-button v-if="getOverride(row.key)" text type="danger" size="small" @click="removeOverride(row.key)">移除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="overrideDialogVisible" :title="`编辑 ${editingRole} 模型路由`" width="520px">
      <el-form label-width="100px">
        <el-form-item label="指定模型">
          <el-select v-model="overrideModelRef" clearable placeholder="留空则继承所属档位" style="width: 100%">
            <el-option v-for="model in libraryModels" :key="model.id" :label="`${model.name || model.id} (${model.model})`" :value="model.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="overrideDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveOverride">保存</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.hint,
.muted {
  color: var(--color-text-muted);
}

.tier-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.tier-card {
  display: grid;
  gap: 8px;
  padding: 14px;
  border: 1px solid #d8e3f2;
  border-radius: 10px;
  background: #f7fbff;
}

.tier-card.reasoning {
  border-color: #ead8b2;
  background: #fffaf0;
}

.tier-card span {
  color: var(--color-text-muted);
  font-size: 12px;
}

.tier-actions {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 14px;
}
</style>
