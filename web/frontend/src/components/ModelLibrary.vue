<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Connection, Delete, Edit, Plus } from '@element-plus/icons-vue'
import { deleteModel, listModels, saveModel, setModelSlot, testModel } from '../api'
import {
  MODEL_SLOT_OPTIONS,
  modelSlotLabel,
  modelSlotTagType,
  type ModelSlot,
} from '../constants/modelSlots'


interface ModelEntry {
  id: string
  name: string
  provider: string
  base_url: string
  model: string
  max_tokens: number
  temperature: number
  timeout: number
  proxy: string
  api_key: string
  has_api_key?: boolean
  type?: string
  slot?: ModelSlot
}

interface PresetModel {
  id: string
  name: string
  provider: string
  brand: string
  base_url: string
  model: string
  max_tokens: number
  temperature: number
  timeout: number
  description: string
  local?: boolean
  type?: string
}

const PRESET_MODELS: PresetModel[] = [
  {
    id: 'openai-gpt-5-2',
    name: 'GPT-5.2',
    provider: 'openai',
    brand: 'OpenAI',
    base_url: 'https://api.openai.com/v1',
    model: 'gpt-5.2',
    max_tokens: 16384,
    temperature: 0.7,
    timeout: 180,
    description: '主力写作、规划和复杂推理。',
  },
  {
    id: 'openai-gpt-5-2-pro',
    name: 'GPT-5.2 Pro',
    provider: 'openai',
    brand: 'OpenAI',
    base_url: 'https://api.openai.com/v1',
    model: 'gpt-5.2-pro',
    max_tokens: 16384,
    temperature: 0.55,
    timeout: 240,
    description: '高质量总编、大纲和关键章节重写。',
  },
  {
    id: 'openai-gpt-5-1-chat',
    name: 'GPT-5.1 Chat',
    provider: 'openai',
    brand: 'OpenAI',
    base_url: 'https://api.openai.com/v1',
    model: 'gpt-5.1-chat-latest',
    max_tokens: 8192,
    temperature: 0.8,
    timeout: 120,
    description: '适合 AI 创作引导和交互式反馈。',
  },
  {
    id: 'deepseek-v4-flash',
    name: 'DeepSeek V4 Flash',
    provider: 'openai',
    brand: 'DeepSeek',
    base_url: 'https://api.deepseek.com/v1',
    model: 'deepseek-v4-flash',
    max_tokens: 8192,
    temperature: 0.7,
    timeout: 120,
    description: '中文草稿、低延迟批量任务。',
  },
  {
    id: 'deepseek-v4-pro',
    name: 'DeepSeek V4 Pro',
    provider: 'openai',
    brand: 'DeepSeek',
    base_url: 'https://api.deepseek.com/v1',
    model: 'deepseek-v4-pro',
    max_tokens: 8192,
    temperature: 0.6,
    timeout: 180,
    description: '剧情逻辑、审稿和复杂拆解。',
  },
  {
    id: 'gemini-3-flash-preview',
    name: 'Gemini 3 Flash Preview',
    provider: 'openai',
    brand: 'Google',
    base_url: 'https://generativelanguage.googleapis.com/v1beta/openai',
    model: 'gemini-3-flash-preview',
    max_tokens: 8192,
    temperature: 0.7,
    timeout: 120,
    description: '快速灵感、摘要和辅助审核。',
  },
  {
    id: 'claude-sonnet-4-6-gateway',
    name: 'Claude Sonnet 4.6（兼容网关）',
    provider: 'openai',
    brand: 'Anthropic',
    base_url: '',
    model: 'claude-sonnet-4-6',
    max_tokens: 8192,
    temperature: 0.65,
    timeout: 180,
    description: '需填写 OpenAI-compatible 网关地址。',
  },
  {
    id: 'claude-opus-4-7-gateway',
    name: 'Claude Opus 4.7（兼容网关）',
    provider: 'openai',
    brand: 'Anthropic',
    base_url: '',
    model: 'claude-opus-4-7',
    max_tokens: 8192,
    temperature: 0.55,
    timeout: 240,
    description: '需填写 OpenAI-compatible 网关地址。',
  },
  {
    id: 'local-ollama-qwen3',
    name: '本地 Ollama（Qwen3）',
    provider: 'openai',
    brand: 'Local',
    base_url: 'http://localhost:11434/v1',
    model: 'qwen3:14b',
    max_tokens: 8192,
    temperature: 0.7,
    timeout: 180,
    description: '本机 Ollama，兼容 OpenAI 接口。',
    local: true,
  },
  {
    id: 'local-lm-studio',
    name: '本地 LM Studio',
    provider: 'openai',
    brand: 'Local',
    base_url: 'http://localhost:1234/v1',
    model: 'local-model',
    max_tokens: 8192,
    temperature: 0.7,
    timeout: 180,
    description: '适合桌面本地模型服务。',
    local: true,
  },
  {
    id: 'local-vllm',
    name: '本地 vLLM / SGLang',
    provider: 'openai',
    brand: 'Local',
    base_url: 'http://localhost:8001/v1',
    model: 'Qwen/Qwen3-32B',
    max_tokens: 8192,
    temperature: 0.7,
    timeout: 240,
    description: '适合自建推理服务和局域网服务。',
    local: true,
  },
  {
    id: 'siliconflow-flux-schnell',
    name: 'FLUX.1 Schnell (硅基流动)',
    provider: 'openai',
    brand: 'SiliconFlow',
    base_url: 'https://api.siliconflow.cn/v1',
    model: 'black-forest-labs/FLUX.1-schnell',
    max_tokens: 1024,
    temperature: 1.0,
    timeout: 90,
    description: '极速、高质量的图像生成模型。用于书库封面绘制（生成封面时候选）。',
    type: 'image',
  },
  {
    id: 'openai-dall-e-3',
    name: 'DALL-E 3 (OpenAI)',
    provider: 'openai',
    brand: 'OpenAI',
    base_url: 'https://api.openai.com/v1',
    model: 'dall-e-3',
    max_tokens: 1024,
    temperature: 1.0,
    timeout: 120,
    description: '官方画图模型，细节丰富，风格多变。用于书库封面绘制。',
    type: 'image',
  },
]

const HIDDEN_PRESETS_KEY = 'novel-agent-hidden-preset-models'

const models = ref<ModelEntry[]>([])
const loading = ref(false)
const expanded = ref(false)
const dialogVisible = ref(false)
const editingId = ref<string | null>(null)
const slotChangingId = ref('')
const applyingId = ref('')
const testResults = ref<Record<string, { loading: boolean; result: any }>>({})
const hiddenPresetIds = ref<string[]>([])

const form = ref({
  id: '',
  name: '',
  provider: 'openai',
  base_url: '',
  api_key: '',
  has_api_key: false,
  model: '',
  max_tokens: 8192,
  temperature: 0.7,
  timeout: 120,
  proxy: '',
  type: 'text',
  slot: '' as ModelSlot,
})

const apiKeyPlaceholder = computed(() => {
  if (form.value.has_api_key && !form.value.api_key) {
    return '已保存 Key（留空不修改；输入新值可覆盖）'
  }
  return '本地模型可留空'
})

const existingIds = computed(() => new Set(models.value.map((m) => m.id)))
const hiddenPresets = computed(() => new Set(hiddenPresetIds.value))
const availablePresets = computed(() => PRESET_MODELS.filter((p) => !existingIds.value.has(p.id) && !hiddenPresets.value.has(p.id)))
const dailyModel = computed(() => models.value.find((m) => m.slot === 'daily'))
const reasoningModel = computed(() => models.value.find((m) => m.slot === 'reasoning'))
const backupModels = computed(() => models.value.filter((m) => m.slot === 'backup'))
const previewModels = computed(() => {
  const picked = [dailyModel.value, reasoningModel.value, ...backupModels.value].filter(Boolean) as ModelEntry[]
  const ids = new Set(picked.map((m) => m.id))
  const rest = textModels.value.filter((m) => !ids.has(m.id))
  return [...picked, ...rest].slice(0, 5)
})
const previewOverflow = computed(() =>
  Math.max(0, textModels.value.length - previewModels.value.length),
)

const textModels = computed(() => models.value.filter(m => !m.type || m.type === 'text'))
const imageModels = computed(() => models.value.filter(m => m.type === 'image'))

const fetchModels = async () => {
  loading.value = true
  try {
    const { data } = await listModels()
    models.value = data
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const onSlotChange = async (id: string, slot: ModelSlot) => {
  slotChangingId.value = id
  try {
    await setModelSlot(id, slot)
    const label = modelSlotLabel(slot)
    ElMessage.success(slot ? `已设为${label}（全局生效）` : '已清除档位')
    await fetchModels()
  } catch (error: any) {
    ElMessage.error(error.message || '档位设置失败')
  } finally {
    slotChangingId.value = ''
  }
}

const presetToEntry = (preset: PresetModel) => ({
  id: preset.id,
  name: preset.name,
  provider: preset.provider,
  base_url: preset.base_url,
  api_key: '',
  has_api_key: false,
  model: preset.model,
  max_tokens: preset.max_tokens,
  temperature: preset.temperature,
  timeout: preset.timeout,
  proxy: '',
  type: preset.type || 'text',
  slot: '' as ModelSlot,
})

const applyPreset = async (preset: PresetModel) => {
  if (!preset.base_url) {
    openPresetDialog(preset)
    ElMessage.info('这个模型需要先填写兼容网关地址，再保存应用。')
    return
  }
  applyingId.value = preset.id
  try {
    await saveModel(presetToEntry(preset))
    ElMessage.success(preset.type === 'image' ? '图像预设已保存' : '预设已保存到模型库')
    await fetchModels()
  } catch (error: any) {
    ElMessage.error(error.message || '应用模型失败')
  } finally {
    applyingId.value = ''
  }
}

const loadHiddenPresets = () => {
  try {
    hiddenPresetIds.value = JSON.parse(localStorage.getItem(HIDDEN_PRESETS_KEY) || '[]')
  } catch {
    hiddenPresetIds.value = []
  }
}

const saveHiddenPresets = () => {
  localStorage.setItem(HIDDEN_PRESETS_KEY, JSON.stringify(hiddenPresetIds.value))
}

const removePreset = async (preset: PresetModel) => {
  try {
    await ElMessageBox.confirm(`确定从预设列表移除「${preset.name}」吗？已配置模型不受影响。`, '删除预设', {
      confirmButtonText: '删除预设',
      cancelButtonText: '取消',
      type: 'warning',
    })
    hiddenPresetIds.value = Array.from(new Set([...hiddenPresetIds.value, preset.id]))
    saveHiddenPresets()
    ElMessage.success('预设已移除')
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('移除预设失败')
  }
}

const restorePresets = () => {
  hiddenPresetIds.value = []
  saveHiddenPresets()
  ElMessage.success('已恢复预设模型')
}

const openPresetDialog = (preset?: PresetModel) => {
  editingId.value = null
  form.value = preset
    ? presetToEntry(preset)
    : {
        id: '',
        name: '',
        provider: 'openai',
        base_url: '',
        api_key: '',
        has_api_key: false,
        model: '',
        max_tokens: 8192,
        temperature: 0.7,
        timeout: 120,
        proxy: '',
        type: 'text',
        slot: '' as ModelSlot,
      }
  dialogVisible.value = true
}

const openEditDialog = (m: ModelEntry) => {
  editingId.value = m.id
  form.value = {
    id: m.id,
    name: m.name || m.id,
    provider: m.provider || 'openai',
    base_url: m.base_url,
    api_key: '',
    has_api_key: Boolean(m.has_api_key),
    model: m.model,
    max_tokens: m.max_tokens || 8192,
    temperature: m.temperature ?? 0.7,
    timeout: m.timeout || 120,
    proxy: m.proxy || '',
    type: m.type || 'text',
    slot: (m.slot || '') as ModelSlot,
  }
  dialogVisible.value = true
}

const handleSave = async () => {
  if (!form.value.id.trim() || !form.value.model.trim()) {
    ElMessage.warning('请填写模型 ID 和服务商模型名')
    return
  }
  const payload = { ...form.value }
  const slot = (form.value.slot || '') as ModelSlot
  delete (payload as { has_api_key?: boolean }).has_api_key
  delete (payload as { slot?: ModelSlot }).slot
  const { data } = await saveModel(payload)
  if ((!form.value.type || form.value.type === 'text') && slot) {
    await setModelSlot(form.value.id.trim(), slot)
  }
  if (data?.has_api_key) {
    form.value.has_api_key = true
  } else if (form.value.api_key.trim()) {
    form.value.has_api_key = true
  }
  form.value.api_key = ''
  ElMessage.success(editingId.value ? '模型配置已保存' : '模型已添加')
  dialogVisible.value = false
  await fetchModels()
}

const handleDelete = async (id: string, name: string) => {
  try {
    await ElMessageBox.confirm(`确定删除模型「${name}」吗？`, '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await deleteModel(id)
    ElMessage.success('已删除')
    await fetchModels()
  } catch (error: any) {
    if (error !== 'cancel') ElMessage.error(error.message || '删除失败')
  }
}

const handleTest = async (id: string) => {
  testResults.value[id] = { loading: true, result: null }
  try {
    const { data } = await testModel({ model_id: id })
    testResults.value[id] = { loading: false, result: data }
  } catch (error: any) {
    testResults.value[id] = { loading: false, result: { success: false, error: error.message } }
  }
}

const getTestStatus = (id: string) => {
  const t = testResults.value[id]
  if (!t) return 'untested'
  if (t.loading) return 'testing'
  return t.result?.success ? 'success' : 'failed'
}

onMounted(async () => {
  loadHiddenPresets()
  await fetchModels()
})

const getBrandClass = (brandName?: string) => {
  if (!brandName) return 'brand-other'
  const b = brandName.toLowerCase()
  if (b.includes('openai')) return 'brand-openai'
  if (b.includes('deepseek')) return 'brand-deepseek'
  if (b.includes('google') || b.includes('gemini')) return 'brand-gemini'
  if (b.includes('anthropic') || b.includes('claude')) return 'brand-anthropic'
  if (b.includes('local') || b.includes('ollama')) return 'brand-local'
  return 'brand-other'
}

const getModelBrandClass = (m: ModelEntry) => {
  const idLower = m.id.toLowerCase()
  const nameLower = (m.name || '').toLowerCase()
  const providerLower = (m.provider || '').toLowerCase()
  if (idLower.includes('deepseek') || nameLower.includes('deepseek')) return 'brand-deepseek'
  if (idLower.includes('gpt') || idLower.includes('openai') || nameLower.includes('gpt') || nameLower.includes('openai')) return 'brand-openai'
  if (idLower.includes('gemini') || nameLower.includes('gemini') || idLower.includes('google') || nameLower.includes('google')) return 'brand-gemini'
  if (idLower.includes('claude') || nameLower.includes('claude') || idLower.includes('anthropic') || nameLower.includes('anthropic')) return 'brand-anthropic'
  if (idLower.includes('local') || idLower.includes('ollama') || idLower.includes('lm-studio') || idLower.includes('vllm')) return 'brand-local'
  
  if (providerLower.includes('openai')) return 'brand-openai'
  if (providerLower.includes('deepseek')) return 'brand-deepseek'
  return 'brand-other'
}

defineExpose({ fetchModels })
</script>

<template>
  <section class="fold-card model-library">
    <div class="fold-head model-head" @click="expanded = !expanded">
      <div class="head-left">
        <span class="collapse-arrow" :class="{ open: expanded }">▶</span>
        <div>
          <h2>模型库</h2>
          <p>
            日常档：{{ dailyModel ? dailyModel.name || dailyModel.id : '未设置' }} ·
            逻辑档：{{ reasoningModel ? reasoningModel.name || reasoningModel.id : '未设置' }} ·
            备用 {{ backupModels.length }} 个 · 共 {{ models.length }} 个模型（档位全局生效）
          </p>
        </div>
      </div>

      <div class="head-preview" @click.stop>
        <span v-if="!models.length" class="model-chip empty">未配置模型</span>
        <span
          v-for="model in previewModels"
          :key="model.id"
          class="model-chip"
          :class="{ main: model.slot === 'daily', warn: model.slot === 'reasoning' }"
          :title="model.model"
        >
          <template v-if="model.slot">{{ modelSlotLabel(model.slot) }} </template>{{ model.name || model.id }}
        </span>
        <span v-if="previewOverflow" class="model-chip">+{{ previewOverflow }}</span>
      </div>

      <el-button class="fold-action" size="small" type="primary" @click.stop="expanded = !expanded">
        {{ expanded ? '收起' : '编辑配置' }}
      </el-button>
    </div>

    <div v-show="expanded" class="fold-body">
      <div class="library-toolbar">
        <div>
          <strong>模型库</strong>
          <span>每模型可选档位：空 / 日常档（唯一）/ 逻辑档（唯一）/ 备用（可多个，失败时 fallback）。</span>
        </div>
        <div class="toolbar-actions">
          <el-button v-if="false && hiddenPresetIds.length" @click="restorePresets">恢复</el-button>
          <el-button type="primary" :icon="Plus" @click="openPresetDialog()">新增自定义模型</el-button>
        </div>
      </div>

      <div v-if="false && availablePresets.length" class="preset-grid">
        <article v-for="preset in availablePresets" :key="preset.id" class="preset-card" :class="[getBrandClass(preset.brand), { local: preset.local }]">
          <div class="card-content">
            <div class="card-title-row">
              <strong>{{ preset.name }}</strong>
              <el-tag v-if="preset.local" size="small" type="success" effect="plain">本地</el-tag>
            </div>
            <small class="brand-tag-line">{{ preset.brand }} · {{ preset.model }}</small>
            <p class="desc-line">{{ preset.description }}</p>
          </div>
          <div class="preset-actions">
            <el-button type="primary" size="small" :loading="applyingId === preset.id" @click="applyPreset(preset)">一键应用</el-button>
            <el-button size="small" text @click="openPresetDialog(preset)">编辑参数</el-button>
            <el-button size="small" text type="danger" @click="removePreset(preset)">删除预设</el-button>
          </div>
        </article>
      </div>

      <div class="configured-title">
        <strong>已配置文字模型</strong>
        <span>在卡片上选择档位；日常/逻辑各限 1 个，备用可多个。</span>
      </div>
      <div class="model-grid" v-loading="loading">
        <article
          v-for="m in textModels"
          :key="m.id"
          class="model-card"
          :class="[getModelBrandClass(m), { 'is-default': m.slot === 'daily', 'is-reasoning': m.slot === 'reasoning' }]"
        >
          <div class="card-top">
            <div class="card-title-container">
              <strong class="model-name-text">{{ m.name || m.id }}</strong>
              <code class="model-code-text">{{ m.model }}</code>
            </div>
            <el-tag
              v-if="m.slot"
              class="default-badge"
              size="small"
              :type="modelSlotTagType(m.slot)"
            >
              {{ modelSlotLabel(m.slot) }}
            </el-tag>
          </div>
          <div class="card-body">
            <p v-if="m.has_api_key" class="key-line">API Key 已配置</p>
            <p v-if="m.proxy" class="proxy-line">代理：{{ m.proxy }}</p>
          </div>
          <div class="card-actions">
            <span class="test-indicator" v-if="getTestStatus(m.id) !== 'untested'">
              <span class="status-dot" :class="getTestStatus(m.id)"></span>
              <span class="status-text">{{ getTestStatus(m.id) === 'testing' ? '测试中' : getTestStatus(m.id) === 'success' ? '可用' : '失败' }}</span>
            </span>
            <div class="action-buttons">
              <el-select
                :model-value="m.slot || ''"
                size="small"
                class="slot-select"
                :disabled="slotChangingId === m.id"
                placeholder="档位"
                @change="(v: ModelSlot) => onSlotChange(m.id, v)"
              >
                <el-option
                  v-for="opt in MODEL_SLOT_OPTIONS"
                  :key="opt.value || 'empty'"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>
              <el-button text type="primary" :loading="testResults[m.id]?.loading" @click="handleTest(m.id)"><el-icon><Connection /></el-icon>测试</el-button>
              <el-button text @click="openEditDialog(m)"><el-icon><Edit /></el-icon>编辑</el-button>
              <el-button text type="danger" @click="handleDelete(m.id, m.name || m.id)"><el-icon><Delete /></el-icon>删除</el-button>
            </div>
          </div>
        </article>
        <el-empty v-if="!loading && !textModels.length" description="还没有配置文字模型，请新增自定义模型。" />
      </div>

      <div class="configured-title" style="margin-top: 30px;">
        <strong>已配置图像模型</strong>
      </div>
      <div class="model-grid" v-loading="loading">
        <article v-for="m in imageModels" :key="m.id" class="model-card" :class="[getModelBrandClass(m)]">
          <div class="card-top">
            <div class="card-title-container">
              <strong class="model-name-text">{{ m.name || m.id }}</strong>
              <code class="model-code-text">{{ m.model }}</code>
            </div>
            <el-tag type="info" size="small" effect="plain">图像模型</el-tag>
          </div>
          <div class="card-body">
            <p v-if="m.has_api_key" class="key-line">API Key 已配置</p>
            <p v-if="m.proxy" class="proxy-line">代理：{{ m.proxy }}</p>
          </div>
          <div class="card-actions">
            <span class="test-indicator" v-if="getTestStatus(m.id) !== 'untested'">
              <span class="status-dot" :class="getTestStatus(m.id)"></span>
              <span class="status-text">{{ getTestStatus(m.id) === 'testing' ? '测试中' : getTestStatus(m.id) === 'success' ? '可用' : '失败' }}</span>
            </span>
            <div class="action-buttons">
              <el-button text type="primary" :loading="testResults[m.id]?.loading" @click="handleTest(m.id)"><el-icon><Connection /></el-icon>测试</el-button>
              <el-button text @click="openEditDialog(m)"><el-icon><Edit /></el-icon>编辑</el-button>
              <el-button text type="danger" @click="handleDelete(m.id, m.name || m.id)"><el-icon><Delete /></el-icon>删除</el-button>
            </div>
          </div>
        </article>
        <div v-if="!loading && !imageModels.length" style="grid-column: span 3; text-align: center; padding: 36px; color: #8a94a6; border: 1px dashed var(--color-border); border-radius: 8px; background: rgba(255, 255, 255, 0.4);">
          还没有配置图像模型。生成封面时需要使用图像模型，请点击上方“新增自定义模型”来添加。
        </div>
      </div>

    </div>

    <el-dialog v-model="dialogVisible" :title="editingId ? '编辑模型' : '新增模型'" width="580px">
      <el-form label-width="112px">
        <el-form-item label="模型类型" required>
          <el-radio-group v-model="form.type">
            <el-radio value="text">文字模型</el-radio>
            <el-radio value="image">图像模型</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="模型 ID" required>
          <el-input v-model="form.id" :disabled="!!editingId" placeholder="唯一标识，如 openai-main" />
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="form.name" placeholder="自定义名称，如 我的主力模型" />
        </el-form-item>
        <el-form-item label="Provider">
          <el-input v-model="form.provider" placeholder="openai" />
        </el-form-item>
        <el-form-item label="Base URL">
          <el-input v-model="form.base_url" placeholder="https://api.example.com/v1 或 http://localhost:11434/v1" />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input
            v-model="form.api_key"
            type="password"
            show-password
            :placeholder="apiKeyPlaceholder"
          />
          <p v-if="form.has_api_key && !form.api_key" class="api-key-hint">当前已保存密钥，无需重复填写</p>
        </el-form-item>
        <el-form-item label="模型名" required>
          <el-input v-model="form.model" placeholder="服务商模型 ID，如 gpt-5.2 或 qwen3:14b" />
        </el-form-item>
        <el-form-item label="Max Tokens">
          <el-input-number v-model="form.max_tokens" :min="256" :max="65536" :step="256" />
        </el-form-item>
        <el-form-item label="Temperature">
          <el-input-number v-model="form.temperature" :min="0" :max="2" :step="0.1" :precision="1" />
        </el-form-item>
        <el-form-item label="超时">
          <el-input-number v-model="form.timeout" :min="10" :max="600" :step="10" />
        </el-form-item>
        <el-form-item label="网络代理">
          <el-input v-model="form.proxy" placeholder="可选，如 http://127.0.0.1:7890" />
        </el-form-item>
        <el-form-item v-if="!form.type || form.type === 'text'" label="全局档位">
          <el-select v-model="form.slot" placeholder="空" style="width: 100%">
            <el-option
              v-for="opt in MODEL_SLOT_OPTIONS"
              :key="opt.value || 'empty'"
              :label="opt.label"
              :value="opt.value"
            />
          </el-select>
          <p class="slot-form-hint">
            {{ MODEL_SLOT_OPTIONS.find((o) => o.value === form.slot)?.hint }}
          </p>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存配置</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.model-library {
  display: block;
}

.model-head {
  flex-wrap: wrap;
}

.head-preview {
  display: flex;
  flex: 1;
  justify-content: flex-end;
  gap: 6px;
  min-width: 260px;
  flex-wrap: wrap;
}

.model-chip {
  max-width: 210px;
  overflow: hidden;
  padding: 4px 9px;
  border: 1px solid #d9e1ec;
  border-radius: 999px;
  background: var(--color-bg-surface-muted);
  color: var(--color-text-muted);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.model-chip.main {
  border-color: rgba(198, 111, 79, 0.45);
  background: #fff4ee;
  color: #a55236;
  font-weight: 700;
}

.model-chip.warn {
  border-color: rgba(217, 119, 6, 0.4);
  background: #fffbeb;
  color: #b45309;
}

.slot-select {
  width: 96px;
  flex-shrink: 0;
}

.slot-form-hint {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--color-text-subtle);
  line-height: 1.4;
}

.model-card.is-reasoning {
  border-color: rgba(217, 119, 6, 0.35);
}

.model-chip.empty {
  color: #8a94a6;
}

.model-chip.missing-config {
  border-color: rgba(239, 68, 68, 0.45);
  background: #fef2f2;
  color: var(--color-danger);
  font-weight: 700;
}

.library-toolbar,
.configured-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 10px;
}

.configured-title {
  margin-top: 24px;
  border-top: 1px solid var(--color-border-subtle);
  padding-top: 20px;
}

.toolbar-actions {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.library-toolbar strong,
.configured-title strong {
  display: block;
  color: #111827;
  font-size: 16px;
  font-weight: 700;
}

.library-toolbar span,
.configured-title span {
  display: block;
  margin-top: 3px;
  color: var(--color-text-muted);
  font-size: 13px;
}

.preset-grid,
.model-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.preset-card,
.model-card {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 8px;
  padding: 12px 16px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(226, 232, 240, 0.9);
  box-shadow: 0 4px 6px -1px rgba(15, 23, 42, 0.02), 0 2px 4px -2px rgba(15, 23, 42, 0.02);
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  overflow: hidden;
}

/* 品牌主题色彩定义 */
.brand-openai {
  --brand-hue: 160;
  --brand-color: hsl(var(--brand-hue), 84%, 25%);
}
.brand-deepseek {
  --brand-hue: 220;
  --brand-color: hsl(var(--brand-hue), 85%, 45%);
}
.brand-gemini {
  --brand-hue: 275;
  --brand-color: hsl(var(--brand-hue), 75%, 55%);
}
.brand-anthropic {
  --brand-hue: 25;
  --brand-color: hsl(var(--brand-hue), 80%, 48%);
}
.brand-local {
  --brand-hue: 145;
  --brand-color: hsl(var(--brand-hue), 65%, 40%);
}
.brand-other {
  --brand-hue: 210;
  --brand-color: hsl(var(--brand-hue), 30%, 50%);
}

/* 渐变指示顶条 */
.preset-card::before,
.model-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 3px;
  background: linear-gradient(90deg, var(--brand-color) 0%, hsla(var(--brand-hue), 90%, 75%, 0.8) 100%);
  opacity: 0.8;
  transition: opacity 0.3s;
}

.preset-card:hover,
.model-card:hover {
  transform: translateY(-4px);
  border-color: hsla(var(--brand-hue), 60%, 70%, 0.5);
  box-shadow: 0 16px 28px -10px hsla(var(--brand-hue), 30%, 20%, 0.15), 
              0 8px 16px -6px hsla(var(--brand-hue), 30%, 20%, 0.10);
}

.preset-card:hover::before,
.model-card:hover::before {
  opacity: 1;
}

.preset-card.local {
  background: linear-gradient(135deg, var(--color-bg-surface) 0%, #f6fdf9 100%);
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.card-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.preset-card strong,
.model-card strong {
  display: block;
  color: var(--color-text-strong);
  font-size: 14.5px;
  font-weight: 700;
}

.brand-tag-line {
  display: block;
  color: var(--brand-color);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.desc-line {
  margin: 4px 0 0;
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 1.5;
}

.preset-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  border-top: 1px dashed var(--color-border);
  padding-top: 8px;
  margin-top: auto;
}

/* 已配置卡片特有样式 */
.card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.card-title-container {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.model-name-text {
  line-height: 1.2;
}

.model-code-text {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 11px;
  color: var(--color-text-muted);
  background: var(--color-bg-hover);
  padding: 2px 6px;
  border-radius: 4px;
  align-self: flex-start;
}

.default-badge {
  background: linear-gradient(90deg, var(--color-warning), var(--color-warning));
  border: none;
  color: white;
  font-weight: 700;
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 4px;
}

.url-line {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 13px;
  text-overflow: ellipsis;
  overflow: hidden;
  white-space: nowrap;
}

.key-line {
  margin: 0;
  color: var(--color-success);
  font-size: 12px;
  font-weight: 600;
}

.proxy-line {
  margin: 0;
  color: var(--color-text-subtle);
  font-size: 12px;
}

.api-key-hint {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--color-text-muted);
}

.card-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  border-top: 1px dashed var(--color-border);
  padding-top: 8px;
  margin-top: auto;
}

.action-buttons .el-button {
  font-size: 12px !important;
  padding: 4px 6px !important;
  height: 28px !important;
}

.test-indicator {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

/* 呼吸灯指示点定义 */
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--color-text-subtle);
  position: relative;
  display: inline-block;
  transition: all 0.3s ease;
}

.status-dot.testing {
  background-color: var(--color-primary);
  animation: pulse-blue 1.2s infinite ease-in-out;
}

.status-dot.success {
  background-color: var(--color-success);
  box-shadow: 0 0 8px var(--color-success);
  animation: pulse-green 1.8s infinite ease-in-out;
}

.status-dot.failed {
  background-color: var(--color-danger);
  box-shadow: 0 0 8px var(--color-danger);
  animation: pulse-red 1.8s infinite ease-in-out;
}

.status-text {
  font-size: 12px;
  color: var(--color-text-muted);
  font-weight: 500;
}

.action-buttons {
  display: flex;
  gap: 2px;
}

/* 日常档强调样式 */
.model-card.is-default {
  --brand-hue: 38;
  --brand-color: hsl(38, 95%, 48%);
  background: linear-gradient(135deg, hsla(40, 100%, 98%, 0.95) 0%, hsla(35, 100%, 96%, 0.95) 100%);
  border: 1.5px solid hsla(38, 85%, 52%, 0.45);
  box-shadow: 0 10px 25px -6px rgba(217, 119, 6, 0.15), 0 5px 12px -4px rgba(217, 119, 6, 0.1);
}

.model-card.is-default::before {
  height: 4px;
  background: linear-gradient(90deg, var(--color-warning) 0%, var(--color-warning) 50%, var(--color-warning) 100%);
}

.model-card.is-default:hover {
  border-color: hsla(38, 90%, 48%, 0.8);
  box-shadow: 0 20px 35px -8px rgba(217, 119, 6, 0.22), 0 10px 20px -6px rgba(217, 119, 6, 0.15);
}

/* 呼吸动画效果 */
@keyframes pulse-green {
  0% {
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
  }
  70% {
    box-shadow: 0 0 0 6px rgba(16, 185, 129, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
  }
}

@keyframes pulse-red {
  0% {
    box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
  }
  70% {
    box-shadow: 0 0 0 6px rgba(239, 68, 68, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(239, 68, 68, 0);
  }
}

@keyframes pulse-blue {
  0% {
    transform: scale(0.85);
    opacity: 0.5;
  }
  50% {
    transform: scale(1.2);
    opacity: 1;
    box-shadow: 0 0 6px var(--color-primary);
  }
  100% {
    transform: scale(0.85);
    opacity: 0.5;
  }
}
</style>
