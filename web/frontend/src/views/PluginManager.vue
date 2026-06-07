<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Refresh, InfoFilled, Upload, Delete, Edit, QuestionFilled } from '@element-plus/icons-vue'
import PluginAuthorHelpDialog from '../components/PluginAuthorHelpDialog.vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listPlugins,
  listUntrustedPlugins,
  trustPlugin,
  togglePlugin,
  updatePluginConfig,
  reloadPlugins,
  installPluginZip,
  deletePlugin,
} from '../api'

interface PluginInfo {
  name: string
  display_name: string
  version: string
  description: string
  author: string
  icon: string
  plugin_type: string
  requires: string[]
  min_core_version: string
  enabled: boolean
  trusted?: boolean
  loaded?: boolean
  installed_version?: string
  config_schema: any
  config: Record<string, any>
  source: string
}

const loading = ref(false)
const pluginsList = ref<PluginInfo[]>([])
const untrustedPlugins = ref<string[]>([])
const searchQuery = ref('')
const selectedType = ref('')
const selectedStatus = ref('')

const pluginTypes = [
  { value: 'pipeline_hook', label: '流水线钩子 (Pipeline Hook)' },
  { value: 'quality_guard', label: '质量检查 (Quality Guard)' },
  { value: 'exporter', label: '文件导出器 (Exporter)' },
  { value: 'llm_provider', label: 'LLM 提供商 (LLM Provider)' },
  { value: 'agent_override', label: 'Agent 替换 (Agent Override)' },
  { value: 'pipeline_phase', label: '流水线阶段 (Pipeline Phase)' },
  { value: 'vector_store', label: '向量数据库 (Vector Store)' },
  { value: 'embedding_provider', label: '文本嵌入 (Embedding)' },
  { value: 'approval_strategy', label: '审批策略 (Approval)' },
  { value: 'rules_extension', label: '规则扩展 (Rules)' },
  { value: 'prompt_enhancer', label: 'Prompt 增强 (Enhancer)' },
  { value: 'event_listener', label: '事件监听 (Listener)' },
  { value: 'web_extension', label: 'Web 页面 (Web Ext)' },
  { value: 'sensitive_scanner', label: '敏感词扫描 (Scanner)' },
  { value: 'command', label: '命令行工具 (Command)' }
]

// Modal control
const detailDialogVisible = ref(false)
const configDialogVisible = ref(false)
const installDialogVisible = ref(false)
const selectedPlugin = ref<PluginInfo | null>(null)
const configForm = ref<Record<string, any>>({})
const configJsonMode = ref(false)
const configJsonText = ref('')
const installUploading = ref(false)
const installDragOver = ref(false)
const installFile = ref<File | null>(null)
const helpDialogVisible = ref(false)

const fetchPlugins = async () => {
  loading.value = true
  try {
    const [pluginsRes, untrustedRes] = await Promise.all([listPlugins(), listUntrustedPlugins()])
    pluginsList.value = pluginsRes.data || []
    untrustedPlugins.value = untrustedRes.data?.plugins || []
  } catch (error: any) {
    ElMessage.error('获取插件列表失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const handleTrust = async (name: string) => {
  try {
    await ElMessageBox.confirm(
      `插件 ${name} 是本地 Python 代码。仅在确认来源可信时继续。`,
      '信任本地插件',
      { type: 'warning', confirmButtonText: '信任并启用', cancelButtonText: '取消' }
    )
    await trustPlugin(name)
    ElMessage.success(`${name} 已信任并启用`)
    await fetchPlugins()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('信任插件失败: ' + (error.response?.data?.detail || error.message))
    }
  }
}

onMounted(() => {
  fetchPlugins()
})

const handleScan = async () => {
  loading.value = true
  try {
    const res = await reloadPlugins()
    ElMessage.success(`重新扫描成功，共加载 ${res.data?.plugins_loaded || 0} 个插件`)
    await fetchPlugins()
  } catch (error: any) {
    ElMessage.error('扫描插件失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const handleToggle = async (plugin: PluginInfo) => {
  const target = !plugin.enabled
  if (target && plugin.source === 'local' && !plugin.trusted) {
    try {
      await ElMessageBox.confirm(
        `启用 ${plugin.display_name} 将信任并加载本地 Python 代码，请确认来源可靠。`,
        '信任并启用',
        { type: 'warning', confirmButtonText: '继续', cancelButtonText: '取消' }
      )
    } catch {
      return
    }
  }
  try {
    const res = await togglePlugin(plugin.name, target)
    plugin.enabled = res.data.enabled
    if (target) plugin.trusted = true
    ElMessage.success(`${plugin.display_name} 已${plugin.enabled ? '启用' : '禁用'}`)
    await fetchPlugins()
  } catch (error: any) {
    ElMessage.error('切换插件状态失败: ' + (error.response?.data?.detail || error.message))
  }
}

const openInstallDialog = () => {
  installFile.value = null
  installDragOver.value = false
  installDialogVisible.value = true
}

const setInstallFile = (file: File | null) => {
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.zip')) {
    ElMessage.warning('请选择 .zip 插件包')
    return
  }
  installFile.value = file
}

const onInstallDrop = (e: DragEvent) => {
  installDragOver.value = false
  e.preventDefault()
  const file = e.dataTransfer?.files?.[0]
  if (file) setInstallFile(file)
}

const onInstallFileChange = (e: Event) => {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (file) setInstallFile(file)
  input.value = ''
}

const submitInstall = async () => {
  if (!installFile.value) {
    ElMessage.warning('请先选择或拖入 .zip 文件')
    return
  }
  installUploading.value = true
  try {
    const res = await installPluginZip(installFile.value)
    ElMessage.success(res.data?.message || '插件安装成功')
    installDialogVisible.value = false
    installFile.value = null
    await fetchPlugins()
  } catch (error: any) {
    ElMessage.error('安装失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    installUploading.value = false
  }
}

const handleDelete = async (plugin: PluginInfo) => {
  try {
    await ElMessageBox.confirm(
      `将删除插件「${plugin.display_name}」及其本地文件，此操作不可恢复。`,
      '删除插件',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await deletePlugin(plugin.name)
    ElMessage.success(`${plugin.display_name} 已删除`)
    await fetchPlugins()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败: ' + (error.response?.data?.detail || error.message))
    }
  }
}

const showDetail = (plugin: PluginInfo) => {
  selectedPlugin.value = plugin
  detailDialogVisible.value = true
}

const hasSchemaForm = (plugin: PluginInfo) =>
  !!(plugin.config_schema?.properties && Object.keys(plugin.config_schema.properties).length > 0)

const showConfig = (plugin: PluginInfo) => {
  selectedPlugin.value = plugin
  configForm.value = JSON.parse(JSON.stringify(plugin.config || {}))
  configJsonMode.value = !hasSchemaForm(plugin)
  configJsonText.value = JSON.stringify(configForm.value, null, 2)

  const properties = plugin.config_schema?.properties || {}
  for (const key in properties) {
    if (configForm.value[key] === undefined || configForm.value[key] === null) {
      if (properties[key].default !== undefined) {
        configForm.value[key] = properties[key].default
      } else if (properties[key].type === 'boolean') {
        configForm.value[key] = false
      } else if (properties[key].type === 'array') {
        configForm.value[key] = []
      } else {
        configForm.value[key] = ''
      }
    }
  }

  configDialogVisible.value = true
}

const saveConfig = async () => {
  if (!selectedPlugin.value) return
  let payload = configForm.value
  if (configJsonMode.value) {
    try {
      payload = JSON.parse(configJsonText.value || '{}')
    } catch {
      ElMessage.error('JSON 格式无效，请检查后再保存')
      return
    }
  }
  try {
    const res = await updatePluginConfig(selectedPlugin.value.name, payload)
    selectedPlugin.value.config = res.data.config
    ElMessage.success(`${selectedPlugin.value.display_name} 配置更新成功`)
    configDialogVisible.value = false
    await fetchPlugins()
  } catch (error: any) {
    ElMessage.error('保存配置失败: ' + (error.response?.data?.detail || error.message))
  }
}

// Search and Filter computation
const filteredPlugins = computed(() => {
  return pluginsList.value.filter((p) => {
    const matchesSearch =
      p.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      p.display_name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      p.description.toLowerCase().includes(searchQuery.value.toLowerCase())
    const matchesType = !selectedType.value || p.plugin_type === selectedType.value
    const matchesStatus =
      !selectedStatus.value ||
      (selectedStatus.value === 'active' && p.enabled) ||
      (selectedStatus.value === 'inactive' && !p.enabled)
    return matchesSearch && matchesType && matchesStatus
  })
})

const totalCount = computed(() => pluginsList.value.length)
const activeCount = computed(() => pluginsList.value.filter((p) => p.enabled).length)

const getTypeLabel = (typeVal: string) => {
  return pluginTypes.find((t) => t.value === typeVal)?.label || typeVal
}
</script>

<template>
  <div class="plugin-manager-view">
    <header class="page-head">
      <div class="page-title-area">
        <h1>🧩 插件生态管理</h1>
        <p>扩展您的创作环境，切换丰富的底层策略、质量保障以及格式导出功能。</p>
      </div>
      <div class="head-actions">
        <el-tooltip content="插件格式与开发说明" placement="bottom">
          <el-button :icon="QuestionFilled" circle @click="helpDialogVisible = true" />
        </el-tooltip>
        <el-button :icon="Upload" type="success" @click="openInstallDialog">载入插件</el-button>
        <el-button :icon="Refresh" type="primary" :loading="loading" @click="handleScan">
          重新扫描
        </el-button>
      </div>
    </header>

    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="新手可从官方示例插件开始"
      style="margin-bottom: 16px"
    >
      复制 <code>plugins/examples/</code> 下的 <code>hello_guard.py</code> 到 <code>plugins/</code> 后启用。
      详见仓库 <code>plugins/examples/README.md</code>。
    </el-alert>

    <el-alert
      v-if="untrustedPlugins.length"
      title="发现尚未信任的本地插件"
      type="warning"
      :closable="false"
      show-icon
      style="margin-bottom: 16px"
    >
      <template #default>
        <span>这些插件在信任前不会执行：</span>
        <el-button
          v-for="name in untrustedPlugins"
          :key="name"
          size="small"
          type="warning"
          plain
          style="margin-left: 8px"
          @click="handleTrust(name)"
        >
          信任 {{ name }}
        </el-button>
      </template>
    </el-alert>

    <!-- Overview Metrics cards -->
    <div class="plugin-metrics">
      <div class="metric-card total-card">
        <span class="m-label">已装插件数</span>
        <span class="m-val">{{ totalCount }}</span>
      </div>
      <div class="metric-card active-card">
        <span class="m-label">启用运行中</span>
        <span class="m-val">{{ activeCount }}</span>
      </div>
    </div>

    <!-- Search & Filter Area -->
    <div class="filter-bar panel">
      <el-input
        v-model="searchQuery"
        placeholder="搜索插件名称、描述..."
        clearable
        class="search-input"
      />
      <el-select v-model="selectedType" placeholder="插件类型" clearable class="filter-select">
        <el-option
          v-for="item in pluginTypes"
          :key="item.value"
          :label="item.label"
          :value="item.value"
        />
      </el-select>
      <el-select v-model="selectedStatus" placeholder="启用状态" clearable class="filter-select-sm">
        <el-option label="已启用" value="active" />
        <el-option label="已禁用" value="inactive" />
      </el-select>
    </div>

    <!-- Plugins Grid -->
    <div v-loading="loading" class="plugins-grid-container">
      <div v-if="filteredPlugins.length > 0" class="plugins-grid">
        <el-card v-for="plugin in filteredPlugins" :key="plugin.name" class="plugin-item-card" shadow="hover">
          <div class="plugin-card-body">
            <!-- Header status & type -->
            <div class="card-top">
              <span class="status-indicator" :class="{ enabled: plugin.enabled }">
                <span class="pulse-dot" v-if="plugin.enabled"></span>
                {{ plugin.enabled ? '运行中' : plugin.trusted === false ? '待信任' : '已禁用' }}
              </span>
              <el-tag size="small" type="info" class="plugin-type-tag">
                {{ plugin.plugin_type }}
              </el-tag>
            </div>

            <!-- Title & description -->
            <div class="plugin-title-info">
              <div class="plugin-display-name">
                <h3>{{ plugin.display_name }}</h3>
                <small class="v-tag">v{{ plugin.version }}</small>
              </div>
              <p class="plugin-desc">{{ plugin.description || '暂无详细说明。' }}</p>
            </div>

            <!-- Bottom meta -->
            <div class="plugin-meta-bottom">
              <div class="author-info">
                <span>作者: {{ plugin.author || '未知' }}</span>
                <span class="source-tag" :class="plugin.source">{{ plugin.source }}</span>
              </div>
            </div>

            <!-- Footer switches & actions -->
            <div class="card-actions">
              <div class="action-left">
                <el-button size="small" :icon="InfoFilled" @click="showDetail(plugin)">
                  详情
                </el-button>
                <el-button size="small" :icon="Edit" @click="showConfig(plugin)">配置</el-button>
                <el-button
                  size="small"
                  type="danger"
                  plain
                  :icon="Delete"
                  @click="handleDelete(plugin)"
                >
                  删除
                </el-button>
              </div>
              <div class="action-right">
                <span class="switch-label">{{ plugin.enabled ? '启用' : '关闭' }}</span>
                <el-switch
                  :model-value="plugin.enabled"
                  active-color="#c66f4f"
                  @change="handleToggle(plugin)"
                />
              </div>
            </div>
          </div>
        </el-card>
      </div>
      <el-empty v-else description="没有找到匹配的插件" />
    </div>

    <PluginAuthorHelpDialog v-model:visible="helpDialogVisible" />

    <!-- Plugin Detail Dialog -->
    <el-dialog v-model="detailDialogVisible" title="ℹ️ 插件详细信息" width="500px" align-center>
      <div v-if="selectedPlugin" class="plugin-detail-dialog-content">
        <div class="detail-row">
          <span class="detail-label">插件名称：</span>
          <span class="detail-value"><strong>{{ selectedPlugin.display_name }}</strong></span>
        </div>
        <div class="detail-row">
          <span class="detail-label">唯一标识：</span>
          <span class="detail-value"><code>{{ selectedPlugin.name }}</code></span>
        </div>
        <div class="detail-row">
          <span class="detail-label">版本：</span>
          <span class="detail-value">v{{ selectedPlugin.version }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">作者：</span>
          <span class="detail-value">{{ selectedPlugin.author || '未知' }}</span>
        </div>
        <div class="detail-row">
          <span class="detail-label">安装来源：</span>
          <span class="detail-value">
            <el-tag :type="selectedPlugin.source === 'local' ? 'warning' : 'success'">
              {{ selectedPlugin.source }}
            </el-tag>
          </span>
        </div>
        <div class="detail-row">
          <span class="detail-label">扩展类型：</span>
          <span class="detail-value">{{ getTypeLabel(selectedPlugin.plugin_type) }}</span>
        </div>
        <div class="detail-row" v-if="selectedPlugin.requires && selectedPlugin.requires.length > 0">
          <span class="detail-label">依赖关系：</span>
          <span class="detail-value">
            <el-tag v-for="req in selectedPlugin.requires" :key="req" size="small" type="danger" style="margin-right: 5px;">
              {{ req }}
            </el-tag>
          </span>
        </div>
        <div class="detail-row">
          <span class="detail-label">最小核心版本：</span>
          <span class="detail-value"><code>{{ selectedPlugin.min_core_version }}</code></span>
        </div>
        <div class="detail-desc-box">
          <strong>插件描述：</strong>
          <p>{{ selectedPlugin.description || '无。' }}</p>
        </div>
      </div>
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- Install Plugin Dialog -->
    <el-dialog v-model="installDialogVisible" title="载入插件" width="480px" align-center>
      <div
        class="install-dropzone"
        :class="{ 'is-dragover': installDragOver, 'has-file': !!installFile }"
        @dragover.prevent="installDragOver = true"
        @dragleave.prevent="installDragOver = false"
        @drop.prevent="onInstallDrop"
      >
        <p class="drop-title">将 .zip 插件包拖放到此处</p>
        <p class="drop-hint">根目录须包含 inkrest.plugin.json</p>
        <input
          id="plugin-zip-input"
          type="file"
          accept=".zip,application/zip"
          class="hidden-file-input"
          @change="onInstallFileChange"
        />
        <label for="plugin-zip-input" class="pick-file-btn">选择文件</label>
        <p v-if="installFile" class="picked-file">{{ installFile.name }}</p>
      </div>
      <template #footer>
        <el-button @click="installDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="installUploading" @click="submitInstall">
          安装
        </el-button>
      </template>
    </el-dialog>

    <!-- Plugin Config Dialog -->
    <el-dialog v-model="configDialogVisible" :title="`⚙️ 配置 - ${selectedPlugin?.display_name}`" width="550px" align-center>
      <div v-if="selectedPlugin" class="plugin-config-form">
        <el-alert
          v-if="configJsonMode"
          type="info"
          :closable="false"
          show-icon
          title="该插件未提供 config_schema，可使用 JSON 编辑参数。"
          style="margin-bottom: 12px"
        />
        <el-input
          v-if="configJsonMode"
          v-model="configJsonText"
          type="textarea"
          :rows="12"
          placeholder='{"key": "value"}'
        />
        <el-form v-else label-position="top">
          <template v-for="(prop, key) in selectedPlugin.config_schema.properties" :key="key">
            <el-form-item :label="prop.title || key">
              <!-- description -->
              <div v-if="prop.description" class="form-item-desc">{{ prop.description }}</div>

              <!-- Boolean (el-switch) -->
              <el-switch
                v-if="prop.type === 'boolean'"
                v-model="configForm[key]"
                active-color="#c66f4f"
              />

              <!-- Array with enum items (checkbox group) -->
              <el-checkbox-group
                v-else-if="prop.type === 'array' && prop.items && prop.items.enum"
                v-model="configForm[key]"
              >
                <el-checkbox
                  v-for="item in prop.items.enum"
                  :key="item"
                  :label="item"
                  :value="item"
                />
              </el-checkbox-group>

              <!-- String with enum (el-select) -->
              <el-select
                v-else-if="prop.type === 'string' && prop.enum"
                v-model="configForm[key]"
                style="width: 100%;"
              >
                <el-option
                  v-for="item in prop.enum"
                  :key="item"
                  :label="item"
                  :value="item"
                />
              </el-select>

              <!-- Normal String (el-input) -->
              <el-input
                v-else
                v-model="configForm[key]"
                :type="prop.type === 'string' && prop.format === 'textarea' ? 'textarea' : 'text'"
                :rows="3"
                placeholder="请输入配置项值"
              />
            </el-form-item>
          </template>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="configDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveConfig">保存配置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.plugin-manager-view {
  display: grid;
  gap: 20px;
}



.install-dropzone {
  border: 2px dashed #d1d5db;
  border-radius: 12px;
  padding: 32px 20px;
  text-align: center;
  transition: border-color 0.2s, background 0.2s;
}

.install-dropzone.is-dragover,
.install-dropzone.has-file {
  border-color: var(--primary);
  background: #fff6f2;
}

.drop-title {
  margin: 0 0 6px;
  font-weight: 700;
  color: #1f2937;
}

.drop-hint {
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--text-muted);
}

.hidden-file-input {
  display: none;
}

.pick-file-btn {
  display: inline-block;
  padding: 8px 16px;
  background: var(--primary);
  color: var(--color-bg-surface);
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
}

.picked-file {
  margin-top: 12px;
  font-size: 13px;
  color: #374151;
  word-break: break-all;
}

.switch-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-right: 8px;
}



.plugin-metrics {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.metric-card {
  background: var(--color-bg-surface);
  border-radius: 16px;
  padding: 22px 24px;
  display: flex;
  flex-direction: column;
  border: 1px solid var(--border-light);
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.02);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 25px rgba(15, 23, 42, 0.06);
}

.total-card {
  background: linear-gradient(135deg, var(--color-bg-surface) 0%, var(--color-bg-surface-muted) 100%);
}

.active-card {
  background: linear-gradient(135deg, var(--color-bg-surface) 0%, #fff6f2 100%);
  border-color: rgba(198, 111, 79, 0.2);
}

.m-label {
  font-size: 13.5px;
  color: var(--text-muted);
  font-weight: 600;
}

.m-val {
  font-size: 34px;
  font-weight: 800;
  color: var(--text-main);
  margin-top: 6px;
}

.active-card .m-val {
  color: var(--primary);
}

.filter-bar {
  display: flex;
  gap: 12px;
  padding: 16px;
  align-items: center;
}

.search-input {
  flex: 1;
}

.filter-select {
  width: 240px;
}

.filter-select-sm {
  width: 140px;
}

.plugins-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.plugin-item-card {
  border-radius: 12px !important;
  overflow: hidden;
  transition: all 0.2s ease;
}

.plugin-item-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08) !important;
  border-color: rgba(198, 111, 79, 0.25) !important;
}

.plugin-card-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 200px;
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-indicator {
  font-size: 12px;
  font-weight: 700;
  color: var(--color-danger);
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.status-indicator.enabled {
  color: var(--color-success);
}

.pulse-dot {
  width: 7px;
  height: 7px;
  background: var(--color-success);
  border-radius: 99px;
  box-shadow: 0 0 0 2px rgba(34, 197, 94, 0.2);
}

.plugin-title-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
}

.plugin-display-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.plugin-display-name h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 800;
  color: #111827;
}

.v-tag {
  background: #eef2f7;
  color: #4b5563;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.plugin-desc {
  margin: 0;
  color: var(--text-muted);
  font-size: 13.5px;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
  overflow: hidden;
}

.plugin-meta-bottom {
  border-top: 1px solid #f3f4f6;
  padding-top: 12px;
}

.author-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: var(--text-muted);
}

.source-tag {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  padding: 1px 5px;
  border-radius: 3px;
  background: #e5e7eb;
}

.source-tag.local {
  background: #fef3c7;
  color: var(--color-warning);
}

.source-tag.entry_point {
  background: #d1fae5;
  color: var(--color-success);
}

.card-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.action-left {
  display: flex;
  gap: 6px;
}

.plugin-detail-dialog-content {
  display: grid;
  gap: 12px;
}

.detail-row {
  display: flex;
  font-size: 14.5px;
}

.detail-label {
  color: var(--text-muted);
  width: 110px;
  flex-shrink: 0;
}

.detail-value {
  color: var(--text-main);
  word-break: break-all;
}

.detail-desc-box {
  margin-top: 14px;
  padding: 12px;
  background: var(--color-bg-surface-muted);
  border-radius: 8px;
  border: 1px solid var(--border-light);
}

.detail-desc-box strong {
  display: block;
  font-size: 13px;
  color: var(--text-main);
  margin-bottom: 6px;
}

.detail-desc-box p {
  margin: 0;
  font-size: 13.5px;
  color: var(--text-muted);
  line-height: 1.6;
}

.form-item-desc {
  font-size: 12.5px;
  color: var(--text-muted);
  line-height: 1.4;
  margin-bottom: 8px;
  width: 100%;
}
</style>
