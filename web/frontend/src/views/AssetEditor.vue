<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Brush, Collection, Delete, Document, FolderOpened, List, MagicStick, Plus, User, View, Warning } from '@element-plus/icons-vue'
import { createAsset, generateAsset, getAsset, listAssets, updateAsset, importToTerminology, deleteAsset } from '../api'

// Sub-editors
import CharacterAssetEditor from '../components/CharacterAssetEditor.vue'
import RulesAssetEditor from '../components/RulesAssetEditor.vue'
import MarkdownAssetEditor from '../components/MarkdownAssetEditor.vue'
import SensitiveWordsConfig from '../components/SensitiveWordsConfig.vue'

type AssetItem = {
  name: string
  label?: string
  path: string
  exists: boolean
  size: number
  custom?: boolean
}

const assetNames: Record<string, string> = {
  character_cards: '角色卡',
  world_bible: '世界观',
  terminology: '名词解释',
  style_guide: '风格指南',
  rules: '写作规则',
  sensitive_words: '敏感词过滤',
}

const assetMeta: Record<string, { group: string; icon: any; tone: string; description: string }> = {
  character_cards: { group: '人物资产', icon: User, tone: 'blue', description: '主角、配角、反派、关系网与出场状态。' },
  world_bible: { group: '设定资产', icon: Collection, tone: 'green', description: '世界规则、地点、势力、资源和禁忌。' },
  terminology: { group: '设定资产', icon: Collection, tone: 'green', description: '专有名词解释、专业术语与特殊名词说明。' },
  style_guide: { group: '写作资产', icon: Brush, tone: 'purple', description: '文风、节奏、对白、镜头和禁用表达。' },
  rules: { group: '写作资产', icon: List, tone: 'orange', description: '章节结构、质量检查、输出格式和流程约束。' },
  sensitive_words: { group: '写作资产', icon: Warning, tone: 'red', description: '与设置→写作规范→敏感词库同一文件；建议主要在设置页编辑。' },
}


type AssetTypeKey = 'character_cards' | 'world_bible' | 'style_guide' | 'rules' | 'custom'

type AssetTypeOption = {
  key: AssetTypeKey
  label: string
  defaultName: string
  defaultLabel: string
  defaultAttributes: string[]
  defaultParameters: Record<string, string>
  helper: string
}

const assetTypeOptions: AssetTypeOption[] = [
  {
    key: 'character_cards',
    label: '角色卡',
    defaultName: 'character_cards',
    defaultLabel: '角色卡',
    defaultAttributes: ['姓名', '定位', '欲望', '秘密', '关系', '出场状态'],
    defaultParameters: { 角色层级: '主角/配角/反派', 关系密度: '高', 冲突方向: '与主线绑定' },
    helper: '适合批量生成主角、配角、反派、组织成员等可复用人物卡。',
  },
  {
    key: 'world_bible',
    label: '世界观',
    defaultName: 'world_bible',
    defaultLabel: '世界观',
    defaultAttributes: ['时代背景', '地理格局', '势力结构', '资源规则', '禁忌', '主线矛盾'],
    defaultParameters: { 世界类型: '都市/玄幻/科幻/历史', 规则硬度: '中', 可扩展性: '长期连载' },
    helper: '适合生成世界规则、地域、势力、技术/能力体系和长期矛盾。',
  },
  {
    key: 'style_guide',
    label: '风格指南',
    defaultName: 'style_guide',
    defaultLabel: '风格指南',
    defaultAttributes: ['叙事人称', '句式节奏', '情绪基调', '对白风格', '描写比例', '禁用表达'],
    defaultParameters: { 文风目标: '网文爽感', 节奏: '快', 读者体感: '清晰有钩子' },
    helper: '适合约束文风、节奏、对白、镜头感和 AI 腔规避策略。',
  },
  {
    key: 'rules',
    label: '写作规则',
    defaultName: 'rules',
    defaultLabel: '写作规则',
    defaultAttributes: ['章节结构', '冲突推进', '伏笔回收', '禁忌事项', '质量检查', '输出格式'],
    defaultParameters: { 平台: '通用', 单章目标: '2000-3000字', 审核强度: '中' },
    helper: '适合生成可被 Agent 读取的规则、检查项、流程约束，优先保存为 YAML。',
  },
  {
    key: 'custom',
    label: '自定义素材',
    defaultName: 'generated_asset',
    defaultLabel: '自定义素材',
    defaultAttributes: ['名称', '用途', '关键设定', '使用场景'],
    defaultParameters: { 输出格式: 'Markdown', 复用方式: '供章节生成参考' },
    helper: '适合地点、组织、道具、案件、职业体系等项目专属素材。',
  },
]

const assets = ref<AssetItem[]>([])
const currentAsset = ref<{ name: string; label?: string; path: string; content: string } | null>(null)
const editContent = ref('')
const showAssetSource = ref(false)
const saving = ref(false)
const loading = ref(false)
const loadError = ref('')
const createDialogVisible = ref(false)
const generateDialogVisible = ref(false)
const creating = ref(false)
const generating = ref(false)

const createForm = ref({
  name: '',
  label: '',
  extension: 'md',
  content: '',
})

const generateForm = ref({
  name: 'generated_asset',
  label: '',
  assetTypeKey: 'character_cards' as AssetTypeKey,
  count: 3,
  attributesText: '',
  parameters: {} as Record<string, string>,
  instructions: '',
})

const selectedAssetType = computed(() =>
  assetTypeOptions.find((item) => item.key === generateForm.value.assetTypeKey) || assetTypeOptions[0]
)

const currentTitle = computed(() => {
  if (!currentAsset.value) return '选择资产'
  return currentAsset.value.label || assetNames[currentAsset.value.name] || currentAsset.value.name
})

const groupedAssets = computed(() => {
  const groups: Record<string, AssetItem[]> = {
    人物资产: [],
    设定资产: [],
    写作资产: [],
    自定义资产: [],
  }
  for (const asset of assets.value) {
    const group = assetMeta[asset.name]?.group || '自定义资产'
    groups[group].push(asset)
  }
  return Object.entries(groups)
    .map(([name, items]) => ({ name, items }))
    .filter((group) => group.items.length)
})

const currentMeta = computed(() => {
  if (!currentAsset.value) return null
  return assetMeta[currentAsset.value.name] || {
    group: '自定义资产',
    icon: Document,
    tone: 'gray',
    description: '项目专属补充素材，可作为章节生成参考。',
  }
})

const isMarkdownAsset = computed(() => {
  if (!currentAsset.value) return false
  return currentAsset.value.path.endsWith('.md')
})

const supportsAssetSource = computed(() => {
  return currentAsset.value?.name === 'character_cards' || isMarkdownAsset.value
})

const contentBlocks = computed(() => {
  const text = editContent.value || ''
  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
  return lines
    .filter((line) => /^#{1,3}\s+/.test(line) || /^[\w\u4e00-\u9fa5_-]+:/.test(line) || /^-\s+/.test(line))
    .slice(0, 12)
    .map((line) => line.replace(/^#{1,3}\s+/, '').replace(/^-\s+/, ''))
})

const apiError = (error: any, fallback: string) =>
  error?.response?.data?.detail || error?.response?.data?.error || error?.message || fallback

const formatSize = (size: number) => {
  if (!size) return '未创建'
  if (size < 1024) return `${size} B`
  return `${(size / 1024).toFixed(1)} KB`
}

const loadAsset = async (name: string) => {
  loading.value = true
  try {
    loadError.value = ''
    const { data } = await getAsset(name)
    currentAsset.value = data
    editContent.value = data.content
    showAssetSource.value = false
  } catch (error: any) {
    loadError.value = apiError(error, '资产加载失败')
  } finally {
    loading.value = false
  }
}

const loadAssets = async () => {
  loading.value = true
  try {
    loadError.value = ''
    const { data } = await listAssets()
    const filtered = (data || []).filter((a: any) => a.name !== 'style_guide' && a.name !== 'rules' && a.name !== 'sensitive_words')
    assets.value = filtered
    if (!currentAsset.value && filtered.length > 0) {
      await loadAsset(filtered[0].name)
    }
  } catch (error: any) {
    loadError.value = apiError(error, '资产列表加载失败')
  } finally {
    loading.value = false
  }
}

const handleSave = async () => {
  if (!currentAsset.value) return
  saving.value = true
  try {
    await updateAsset(currentAsset.value.name, editContent.value)
    ElMessage.success('资产已保存')
    await loadAssets()
  } catch (error: any) {
    ElMessage.error(apiError(error, '保存失败'))
  } finally {
    saving.value = false
  }
}

// 名词解释新增状态与方法
const addTermDialogOpen = ref(false)
const addTermForm = ref({
  name: '',
  description: '',
})

const openAddTermDialog = () => {
  addTermForm.value = {
    name: '',
    description: '',
  }
  addTermDialogOpen.value = true
}

const handleAddTerm = async () => {
  if (!addTermForm.value.name.trim()) {
    ElMessage.warning('请填写名词名称')
    return
  }
  if (!addTermForm.value.description.trim()) {
    ElMessage.warning('请填写名词解释')
    return
  }

  // 物理追加到 editContent
  const currentContent = editContent.value || ''
  const suffix = currentContent.endsWith('\n') ? '' : '\n'
  const newTermText = `${suffix}- **${addTermForm.value.name.trim()}**：${addTermForm.value.description.trim()}\n`
  editContent.value = currentContent + newTermText

  addTermDialogOpen.value = false
  
  // 自动保存
  await handleSave()
}

const handleCreate = async () => {
  if (!createForm.value.name.trim()) {
    ElMessage.warning('请填写资产标识')
    return
  }
  creating.value = true
  try {
    await createAsset(createForm.value)
    ElMessage.success('资产已新增')
    createDialogVisible.value = false
    await loadAssets()
    await loadAsset(createForm.value.name)
  } catch (error: any) {
    ElMessage.error(apiError(error, '新增失败'))
  } finally {
    creating.value = false
  }
}

const parseParameters = () => {
  return Object.fromEntries(
    Object.entries(generateForm.value.parameters)
      .map(([key, value]) => [key.trim(), String(value || '').trim()])
      .filter(([key, value]) => key && value)
  )
}

const applyAssetTypeDefaults = (option: AssetTypeOption, forceName = false) => {
  if (forceName || !generateForm.value.name || generateForm.value.name === 'generated_asset') {
    generateForm.value.name = option.defaultName
  }
  if (forceName || !generateForm.value.label) {
    generateForm.value.label = option.defaultLabel
  }
  generateForm.value.attributesText = option.defaultAttributes.join(',')
  generateForm.value.parameters = { ...option.defaultParameters }
}

const openGenerateDialog = () => {
  applyAssetTypeDefaults(selectedAssetType.value)
  generateDialogVisible.value = true
}

watch(
  () => generateForm.value.assetTypeKey,
  () => applyAssetTypeDefaults(selectedAssetType.value, true)
)

const handleGenerate = async () => {
  if (!generateForm.value.name.trim()) {
    ElMessage.warning('请填写保存标识')
    return
  }
  generating.value = true
  try {
    const { data } = await generateAsset({
      name: generateForm.value.name,
      label: generateForm.value.label,
      asset_type: selectedAssetType.value.label,
      count: generateForm.value.count,
      attributes: generateForm.value.attributesText.split(',').map((item) => item.trim()).filter(Boolean),
      parameters: parseParameters(),
      instructions: generateForm.value.instructions,
    })
    ElMessage.success('AI 素材已生成')
    generateDialogVisible.value = false
    await loadAssets()
    await loadAsset(data.name)
  } catch (error: any) {
    ElMessage.error(apiError(error, 'AI 生成失败'))
  } finally {
    generating.value = false
  }
}

// ---- Custom Assets Batch Selection & Right-click Actions ----
const selectedCustomAssets = ref<string[]>([])

const isAllCustomSelected = computed(() => {
  const customItems = assets.value.filter((a) => a.custom)
  if (customItems.length === 0) return false
  return customItems.every((a) => selectedCustomAssets.value.includes(a.name))
})

const isCustomIndeterminate = computed(() => {
  const customItems = assets.value.filter((a) => a.custom)
  if (customItems.length === 0) return false
  const selectedCount = customItems.filter((a) => selectedCustomAssets.value.includes(a.name)).length
  return selectedCount > 0 && selectedCount < customItems.length
})

const handleToggleSelectAllCustom = (val: any) => {
  const customItems = assets.value.filter((a) => a.custom)
  if (val) {
    selectedCustomAssets.value = customItems.map((a) => a.name)
  } else {
    selectedCustomAssets.value = []
  }
}

const handleToggleSelectAsset = (name: string) => {
  const idx = selectedCustomAssets.value.indexOf(name)
  if (idx > -1) {
    selectedCustomAssets.value.splice(idx, 1)
  } else {
    selectedCustomAssets.value.push(name)
  }
}

const handleBulkImportToTerminology = async () => {
  if (selectedCustomAssets.value.length === 0) return
  try {
    await ElMessageBox.confirm(
      `确定要将选中的 ${selectedCustomAssets.value.length} 个自定义资产导入到“名词解释”中吗？`,
      '导入名词解释',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'info' }
    )
    await importToTerminology({ names: selectedCustomAssets.value })
    ElMessage.success('导入成功！')
    selectedCustomAssets.value = []
    await loadAssets()
    await loadAsset('terminology')
  } catch (error: any) {
    if (error !== 'cancel') ElMessage.error(error.message || '导入失败')
  }
}

const handleBulkDelete = async () => {
  if (selectedCustomAssets.value.length === 0) return
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedCustomAssets.value.length} 个自定义资产吗？该操作不可撤销。`,
      '批量删除资产',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    loading.value = true
    for (const name of selectedCustomAssets.value) {
      await deleteAsset(name)
    }
    ElMessage.success('批量删除成功！')
    const deletedNames = [...selectedCustomAssets.value]
    selectedCustomAssets.value = []
    if (currentAsset.value && deletedNames.includes(currentAsset.value.name)) {
      currentAsset.value = null
    }
    await loadAssets()
  } catch (error: any) {
    if (error !== 'cancel') ElMessage.error(error.message || '删除失败')
  } finally {
    loading.value = false
  }
}

const handleContextCommand = async (command: string, asset: AssetItem) => {
  if (command === 'import_to_terminology') {
    let targetNames = [asset.name]
    if (selectedCustomAssets.value.includes(asset.name) && selectedCustomAssets.value.length > 0) {
      targetNames = [...selectedCustomAssets.value]
    }
    try {
      await importToTerminology({ names: targetNames })
      ElMessage.success('成功导入名词解释！')
      selectedCustomAssets.value = selectedCustomAssets.value.filter((name) => !targetNames.includes(name))
      await loadAssets()
      await loadAsset('terminology')
    } catch (error: any) {
      ElMessage.error(error.message || '导入失败')
    }
  } else if (command === 'delete_asset') {
    try {
      await ElMessageBox.confirm(
        `确定要删除自定义资产「${asset.label || asset.name}」吗？该操作不可撤销。`,
        '删除资产',
        { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
      )
      await deleteAsset(asset.name)
      ElMessage.success('资产已删除')
      selectedCustomAssets.value = selectedCustomAssets.value.filter((name) => name !== asset.name)
      if (currentAsset.value?.name === asset.name) {
        currentAsset.value = null
      }
      await loadAssets()
    } catch (error: any) {
      if (error !== 'cancel') ElMessage.error(error.message || '删除失败')
    }
  }
}

onMounted(loadAssets)
</script>

<template>
  <section class="asset-editor">
    <header class="page-head">
      <div class="page-title-area">
        <h1>资产编辑</h1>
        <p>维护角色、世界观、规则等项目素材；可手写、新增，也可让 AI 批量生成。</p>
      </div>
      <div class="head-actions">
        <el-button :icon="FolderOpened" @click="loadAssets">刷新</el-button>
        <el-button :icon="Plus" @click="createDialogVisible = true">新增资产</el-button>
        <el-button type="primary" :icon="MagicStick" @click="openGenerateDialog">AI 生成</el-button>
      </div>
    </header>

    <el-alert v-if="loadError" :title="loadError" type="warning" show-icon class="error-bar" />

    <div class="asset-layout">
      <aside class="asset-list">
        <div v-for="group in groupedAssets" :key="group.name" class="asset-group">
          <div class="asset-group-title">
            <span>{{ group.name }}</span>
            <div v-if="group.name === '自定义资产'" class="custom-group-actions">
              <el-checkbox
                v-if="group.items.length"
                :model-value="isAllCustomSelected"
                :indeterminate="isCustomIndeterminate"
                @change="handleToggleSelectAllCustom"
                style="margin-right: 8px; height: auto;"
              />
              <el-button
                v-if="selectedCustomAssets.length"
                size="small"
                type="primary"
                link
                @click="handleBulkImportToTerminology"
              >
                导入名词解释({{ selectedCustomAssets.length }})
              </el-button>
              <el-button
                v-if="selectedCustomAssets.length"
                size="small"
                type="danger"
                link
                @click="handleBulkDelete"
                style="margin-left: 8px;"
              >
                批量删除({{ selectedCustomAssets.length }})
              </el-button>
            </div>
            <em v-else>{{ group.items.length }}</em>
          </div>

          <div v-for="asset in group.items" :key="asset.name" class="asset-row-wrapper">
            <el-dropdown
              trigger="contextmenu"
              placement="bottom-start"
              :disabled="group.name !== '自定义资产'"
              style="width: 100%; display: block;"
              @command="(cmd: any) => handleContextCommand(cmd, asset)"
            >
              <div
                class="asset-row"
                :class="{ active: currentAsset?.name === asset.name }"
                @click="loadAsset(asset.name)"
              >
                <el-checkbox
                  v-if="group.name === '自定义资产'"
                  :model-value="selectedCustomAssets.includes(asset.name)"
                  @change="() => handleToggleSelectAsset(asset.name)"
                  @click.stop
                  style="margin-right: 4px; height: auto;"
                />
                <span class="asset-row-icon" :class="assetMeta[asset.name]?.tone || 'gray'">
                  <el-icon><component :is="assetMeta[asset.name]?.icon || Document" /></el-icon>
                </span>
                <span class="asset-row-main">
                  <strong>{{ asset.label || assetNames[asset.name] || asset.name }}</strong>
                  <small>{{ asset.path }}</small>
                </span>
                <span class="asset-row-size">{{ formatSize(asset.size) }}</span>
              </div>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="import_to_terminology" :icon="Collection">
                    导入子设定 (名词解释)
                  </el-dropdown-item>
                  <el-dropdown-item command="delete_asset" :icon="Delete" style="color: #f56c6c;">
                    删除资产
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </aside>

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
              @click="openAddTermDialog"
            >
              ➕ 新增名词
            </el-button>
            <el-button type="primary" :loading="saving" :disabled="!currentAsset" @click="handleSave">
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
          <!-- Character cards (YAML) editor -->
          <CharacterAssetEditor
            v-if="currentAsset.name === 'character_cards'"
            v-model="editContent"
            :show-source="showAssetSource"
            @save="handleSave"
          />

          <!-- Rules (YAML) editor -->
          <RulesAssetEditor
            v-else-if="currentAsset.name === 'rules'"
            v-model="editContent"
            @save="handleSave"
          />

          <!-- Sensitive words editor -->
          <SensitiveWordsConfig
            v-else-if="currentAsset.name === 'sensitive_words'"
            v-model="editContent"
          />

          <!-- Markdown (.md) editor -->
          <MarkdownAssetEditor
            v-else-if="isMarkdownAsset"
            v-model="editContent"
            :title="currentTitle"
            :path="currentAsset.path"
            :show-source="showAssetSource"
            @save="handleSave"
          />

          <!-- Default fallback editor -->
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
    </div>

    <!-- Create Asset Dialog -->
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
        <el-button type="primary" :loading="creating" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- AI Generate Dialog -->
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
        <el-button type="primary" :loading="generating" @click="handleGenerate">生成并保存</el-button>
      </template>
    </el-dialog>

    <!-- 新增名词解释对话框 -->
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
        <el-button type="primary" @click="handleAddTerm">确定并追加</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.asset-editor {
  display: grid;
  gap: 18px;
}



.error-bar {
  border-radius: 8px;
}

.asset-layout {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 16px;
  min-height: calc(100vh - 210px);
}

.asset-list,
.editor-panel {
  background: var(--color-bg-surface);
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.05);
}

.asset-list {
  padding: 8px;
  overflow: auto;
}

.asset-group {
  display: grid;
  gap: 6px;
  margin-bottom: 12px;
}

.asset-group-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px 2px;
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 800;
}

.asset-group-title em {
  font-style: normal;
  color: var(--color-text-subtle);
}

.asset-row-wrapper {
  margin-bottom: 2px;
}

.asset-row {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  color: #1f2937;
  text-align: left;
  cursor: pointer;
  box-sizing: border-box;
}


.asset-row:hover,
.asset-row.active {
  background: var(--color-bg-surface-muted);
  border-color: #dbe2ea;
}

.asset-row.active {
  box-shadow: inset 3px 0 0 #c66f4f;
}

.asset-row-icon {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: #eef6fb;
  color: #2f6f90;
}

.asset-row-icon.blue { background: #eef6fb; color: #2f6f90; }
.asset-row-icon.green { background: #ecfdf5; color: #15803d; }
.asset-row-icon.purple { background: #f5f3ff; color: #6d4cc2; }
.asset-row-icon.orange { background: #fff4ee; color: #b65f3e; }
.asset-row-icon.gray { background: var(--color-bg-hover); color: var(--color-text-muted); }

.asset-row-main {
  min-width: 0;
  display: grid;
  gap: 2px;
  flex: 1;
}

.asset-row-main strong,
.asset-row-main small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.asset-row-main strong {
  font-size: 15px;
}

.asset-row-main small {
  color: #7b8494;
  font-size: 13px;
}

.asset-row-size {
  color: #7b8494;
  font-size: 13px;
  margin-left: auto;
  flex-shrink: 0;
}

.custom-group-actions {
  display: flex;
  align-items: center;
}


.editor-panel {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  overflow: hidden;
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
  .asset-layout {
    grid-template-columns: 1fr;
  }

  .type-helper,
  .type-panel {
    margin-left: 0;
  }

  .parameter-grid {
    grid-template-columns: 1fr;
  }
}
</style>
