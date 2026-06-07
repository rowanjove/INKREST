<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed } from 'vue'
import { ElMessage, ElNotification } from 'element-plus'
import { CircleCheck, Warning, Cpu, Cloudy, Timer } from '@element-plus/icons-vue'
import api, {
  getEmbeddingStatus,
  startSetupLocal,
  getSetupLocalStatus,
  updateConfig,
  rebuildEmbeddingIndex,
} from '../api'
import {
  EMBEDDING_CLOUD_PRESETS,
  resolveEmbeddingCloudEndpoint,
  type EmbeddingCloudPreset,
} from '../constants/embeddingPresets'

const loading = ref(false)
const expanded = ref(false)
const testingCloud = ref(false)
const rebuildingIndex = ref(false)
const activeTab = ref<'local' | 'cloud' | 'stub'>('local')

const envStatus = ref({
  has_onnx: false,
  has_transformers: false,
  has_model: false,
  provider: 'stub',
  model_path: null as string | null,
  vector_enabled: true,
  semantic_search_effective: false,
  work_scale: 'medium',
  long_form_vector_recommended: false,
})

const setupState = ref({
  status: 'idle' as string,
  step: '',
  progress: 0,
  message: '',
  error: null as string | null,
})

const cloudForm = ref({
  provider: 'zhipu',
  base_url: 'https://open.bigmodel.cn/api/paas/v4',
  api_key: '',
  model: 'text-embedding-3',
})

const activeCloudPresetId = ref('zhipu')

const cloudPresets = EMBEDDING_CLOUD_PRESETS

const showCloudModelField = computed(
  () => cloudForm.value.provider === 'openai' || cloudForm.value.provider === 'dashscope',
)

const showCloudBaseUrlField = computed(() => cloudForm.value.provider === 'openai')

let statusTimer: number | null = null

const providerLabel = computed(() => {
  const p = envStatus.value.provider
  if (p === 'local') return '本地 BGE-Micro'
  if (p === 'stub') return 'Stub（关键词）'
  if (p === 'zhipu') return '云端 · 智谱'
  if (p === 'dashscope' || p === 'bailian') return '云端 · 阿里百炼'
  if (p === 'openai') return '云端 · OpenAI 兼容'
  return p
})

const semanticOk = computed(() => envStatus.value.semantic_search_effective)
const vectorOn = computed(() => envStatus.value.vector_enabled !== false)
const vectorDegraded = computed(() => vectorOn.value && !semanticOk.value)
const depsReady = computed(
  () => envStatus.value.has_onnx && envStatus.value.has_transformers && envStatus.value.has_model,
)

const statusTone = computed(() => {
  if (!vectorOn.value) return 'muted'
  if (semanticOk.value) return 'ok'
  return 'warn'
})

const load = async () => {
  loading.value = true
  try {
    const { data } = await getEmbeddingStatus()
    envStatus.value = data
    if (data.provider === 'local') {
      activeTab.value = 'local'
    } else if (
      data.provider === 'openai' ||
      data.provider === 'zhipu' ||
      data.provider === 'dashscope' ||
      data.provider === 'bailian'
    ) {
      activeTab.value = 'cloud'
      const provider = data.provider === 'bailian' ? 'dashscope' : data.provider
      cloudForm.value.provider = provider
      cloudForm.value.api_key = data.api_key || ''
      const configResp = await api.get('/config')
      const emb = configResp.data.embedding || {}
      const resolved = resolveEmbeddingCloudEndpoint(
        provider,
        emb.base_url || '',
        emb.model || '',
      )
      cloudForm.value.base_url = resolved.base_url
      cloudForm.value.model = resolved.model
      const matched = cloudPresets.find(
        (p) =>
          p.provider === provider &&
          p.base_url === resolved.base_url &&
          p.model === resolved.model,
      )
      activeCloudPresetId.value = matched?.id || provider
    } else {
      activeTab.value = 'stub'
    }
    if (data.long_form_vector_recommended) {
      expanded.value = true
    }
  } catch (e: unknown) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const startPollingStatus = () => {
  if (statusTimer) window.clearInterval(statusTimer)
  statusTimer = window.setInterval(async () => {
    try {
      const { data } = await getSetupLocalStatus()
      setupState.value = data
      if (data.status === 'completed') {
        window.clearInterval(statusTimer!)
        statusTimer = null
        ElNotification({
          title: '本地向量已就绪',
          message: '已切换为本地 BGE 嵌入并完成配置。',
          type: 'success',
        })
        await load()
      } else if (data.status === 'failed') {
        window.clearInterval(statusTimer!)
        statusTimer = null
        ElMessage.error(`部署失败: ${data.error}`)
      }
    } catch (e: unknown) {
      console.error(e)
    }
  }, 1000)
}

const handleLocalDeploy = async () => {
  try {
    const { data } = await startSetupLocal()
    if (data.status === 'started' || data.status === 'already_running') {
      setupState.value.status = 'running'
      setupState.value.progress = 5
      setupState.value.message = '正在准备安装环境…'
      startPollingStatus()
    }
  } catch (e: any) {
    ElMessage.error(e.message || '无法启动部署')
  }
}

const applyCloudPreset = (preset: EmbeddingCloudPreset) => {
  activeCloudPresetId.value = preset.id
  cloudForm.value.provider = preset.provider
  cloudForm.value.base_url = preset.base_url
  cloudForm.value.model = preset.model
}

const handleCloudSave = async () => {
  if (!cloudForm.value.api_key.trim()) {
    ElMessage.warning('请输入 API Key')
    return
  }
  testingCloud.value = true
  try {
    const { base_url, model } = resolveEmbeddingCloudEndpoint(
      cloudForm.value.provider,
      cloudForm.value.base_url,
      cloudForm.value.model,
    )

    const testResp = await api.post('/config/embedding/test', {
      provider: cloudForm.value.provider,
      base_url,
      api_key: cloudForm.value.api_key.trim(),
      model,
    })

    if (!testResp.data.success) {
      ElMessage.error('连接失败: ' + testResp.data.error)
      return
    }

    await updateConfig({
      embedding: {
        provider: cloudForm.value.provider,
        base_url,
        api_key: cloudForm.value.api_key.trim(),
        model,
      },
    })

    ElMessage.success('云端嵌入配置已保存（全局生效，所有书籍共用）')
    await load()
  } catch (e: any) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    testingCloud.value = false
  }
}

const handleSkipSetup = async () => {
  try {
    await updateConfig({ embedding: { provider: 'stub' } })
    ElMessage.info('已切换为 Stub 关键词匹配')
    await load()
  } catch (e: any) {
    ElMessage.error(e.message || '切换失败')
  }
}

const handleRebuildIndex = async () => {
  rebuildingIndex.value = true
  try {
    const { data } = await rebuildEmbeddingIndex()
    ElMessage.success(`索引已重建（${JSON.stringify(data.dimensions || {})}）`)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error.message || '重建失败')
  } finally {
    rebuildingIndex.value = false
  }
}

onMounted(() => {
  load()
  getSetupLocalStatus()
    .then(({ data }) => {
      setupState.value = data
      if (data.status === 'running') startPollingStatus()
    })
    .catch((e) => {
      console.error('获取本地安装状态失败:', e)
    })
})

onBeforeUnmount(() => {
  if (statusTimer) window.clearInterval(statusTimer)
})

defineExpose({ load })
</script>

<template>
  <section id="embedding-config" class="fold-card embedding-section" v-loading="loading">
    <div class="fold-head" @click="expanded = !expanded">
      <div class="head-left">
        <span class="collapse-arrow" :class="{ open: expanded }">▶</span>
        <div>
          <h2>向量嵌入</h2>
          <p>
            跨章语义去重、伏笔召回与状态库检索；当前
            <strong :class="`tone-${statusTone}`">{{ providerLabel }}</strong>
            <template v-if="vectorOn">
              · 语义检索{{ semanticOk ? '已生效' : '未生效' }}
            </template>
            <template v-else> · 当前体量未启用向量</template>
          </p>
        </div>
      </div>
      <div class="head-badge" @click.stop>
        <span class="status-pill" :class="statusTone">
          <el-icon v-if="statusTone === 'ok'"><CircleCheck /></el-icon>
          <el-icon v-else-if="statusTone === 'warn'"><Warning /></el-icon>
          {{ statusTone === 'ok' ? '就绪' : statusTone === 'warn' ? '待配置' : '已关闭' }}
        </span>
      </div>
    </div>

    <div v-show="expanded" class="fold-body">
      <el-alert
        v-if="vectorDegraded"
        type="warning"
        :closable="false"
        show-icon
        title="语义检索未生效"
        class="emb-alert"
      >
        长篇/超长篇已开启向量能力，但当前为 Stub 或未配置密钥。重复剧情检测与语义召回不会真正执行，请选择下方方案之一。
      </el-alert>
      <el-alert
        v-else-if="!vectorOn"
        type="info"
        :closable="false"
        show-icon
        title="短篇体量无需向量"
        class="emb-alert"
      >
        微型/短篇档位默认关闭向量索引；在工作台升级体量后会自动要求配置嵌入。
      </el-alert>

      <div class="status-grid">
        <div class="status-cell">
          <span class="cell-label">当前方案</span>
          <span class="cell-value">{{ providerLabel }}</span>
        </div>
        <div class="status-cell">
          <span class="cell-label">语义检索</span>
          <span class="cell-value" :class="{ ok: semanticOk, warn: vectorOn && !semanticOk }">
            {{ !vectorOn ? '体量已关闭' : semanticOk ? '生效中' : '未生效' }}
          </span>
        </div>
        <div class="status-cell">
          <span class="cell-label">本地依赖</span>
          <span class="cell-value" :class="{ ok: depsReady }">
            {{
              envStatus.has_onnx && envStatus.has_transformers && envStatus.has_model
                ? '环境 + 模型就绪'
                : envStatus.has_model
                  ? '模型已下载'
                  : '未部署'
            }}
          </span>
        </div>
      </div>

      <p class="section-label">选择嵌入方案</p>
      <div class="mode-grid">
        <button
          type="button"
          class="mode-card"
          :class="{ active: activeTab === 'local' }"
          @click="activeTab = 'local'"
        >
          <el-icon class="mode-icon local"><Cpu /></el-icon>
          <span class="mode-title">本地 BGE</span>
          <span class="mode-desc">离线 · 约 45MB 模型</span>
        </button>
        <button
          type="button"
          class="mode-card"
          :class="{ active: activeTab === 'cloud' }"
          @click="activeTab = 'cloud'"
        >
          <el-icon class="mode-icon cloud"><Cloudy /></el-icon>
          <span class="mode-title">云端 API</span>
          <span class="mode-desc">智谱 / 百炼 / OpenAI</span>
        </button>
        <button
          type="button"
          class="mode-card"
          :class="{ active: activeTab === 'stub' }"
          @click="activeTab = 'stub'"
        >
          <el-icon class="mode-icon stub"><Timer /></el-icon>
          <span class="mode-title">暂不配置</span>
          <span class="mode-desc">Stub 关键词匹配</span>
        </button>
      </div>

      <div class="mode-panel">
        <template v-if="activeTab === 'local'">
          <div class="panel-intro local">
            <p>
              主程序不包含大型推理库。一键部署将下载 BGE-Micro 与 onnxruntime，在本地 CPU 完成向量化，稿件不出本机。
            </p>
          </div>
          <div class="dep-chips">
            <span class="dep-chip" :class="{ ok: envStatus.has_onnx && envStatus.has_transformers }">
              Python 库 {{ envStatus.has_onnx && envStatus.has_transformers ? '✓' : '—' }}
            </span>
            <span class="dep-chip" :class="{ ok: envStatus.has_model }">
              BGE 模型 {{ envStatus.has_model ? '✓' : '—' }}
            </span>
          </div>
          <div class="panel-action">
            <template v-if="setupState.status === 'running'">
              <p class="running-text">{{ setupState.message }}</p>
              <el-progress
                :percentage="setupState.progress"
                :stroke-width="10"
                striped
                striped-flow
              />
            </template>
            <template v-else-if="setupState.status === 'completed' || (envStatus.provider === 'local' && semanticOk)">
              <div class="done-banner">
                <el-icon><CircleCheck /></el-icon>
                <div>
                  <strong>本地嵌入已启用</strong>
                  <p>正在使用 CPU 版 BGE-Micro 做语义关联。</p>
                </div>
              </div>
            </template>
            <template v-else>
              <el-button type="primary" size="large" @click="handleLocalDeploy">
                一键下载并部署
              </el-button>
              <p v-if="setupState.status === 'failed'" class="fail-hint">
                上次失败：{{ setupState.error }}
              </p>
            </template>
          </div>
        </template>

        <template v-else-if="activeTab === 'cloud'">
          <div class="panel-intro cloud">
            <p>向量计算在云端完成，本机无需安装 onnx 依赖，适合低配置设备或已有 API 额度。</p>
          </div>
          <p class="preset-label">云端预置</p>
          <div class="preset-grid">
            <button
              v-for="preset in cloudPresets"
              :key="preset.id"
              type="button"
              class="preset-chip"
              :class="{ active: activeCloudPresetId === preset.id }"
              @click="applyCloudPreset(preset)"
            >
              <span class="preset-name">{{ preset.name }}</span>
              <span class="preset-model">{{ preset.model }}</span>
            </button>
          </div>

          <el-form label-position="top" class="cloud-form">
            <div class="form-row">
              <el-form-item label="服务商">
                <el-select
                  v-model="cloudForm.provider"
                  style="width: 100%"
                  @change="activeCloudPresetId = ''"
                >
                  <el-option label="智谱 AI" value="zhipu" />
                  <el-option label="阿里百炼（DashScope）" value="dashscope" />
                  <el-option label="OpenAI 兼容" value="openai" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="showCloudModelField" label="模型名称">
                <el-input
                  v-model="cloudForm.model"
                  :placeholder="cloudForm.provider === 'dashscope' ? 'text-embedding-v3' : 'text-embedding-3-small'"
                />
              </el-form-item>
            </div>
            <el-form-item v-if="showCloudBaseUrlField" label="接口地址">
              <el-input v-model="cloudForm.base_url" placeholder="https://api.openai.com/v1" />
            </el-form-item>
            <p v-else-if="cloudForm.provider === 'dashscope'" class="endpoint-hint">
              默认接口：https://dashscope.aliyuncs.com/compatible-mode/v1（百炼控制台 API Key）
            </p>
            <el-form-item label="API Key">
              <el-input
                v-model="cloudForm.api_key"
                type="password"
                show-password
                placeholder="智谱 / 百炼 DashScope / OpenAI Key"
              />
            </el-form-item>
          </el-form>
          <div class="panel-action end">
            <el-button type="primary" :loading="testingCloud" @click="handleCloudSave">
              测试连接并保存
            </el-button>
          </div>
        </template>

        <template v-else>
          <div class="panel-intro stub">
            <p>
              使用轻量关键词匹配，不下载模型。写作与生成不受影响，仅跨章语义去重与向量伏笔召回精度下降。
            </p>
          </div>
          <div class="panel-action center">
            <el-button @click="handleSkipSetup">确认使用 Stub</el-button>
          </div>
        </template>
      </div>

      <div class="tools-row">
        <span class="tools-hint">维护：切换方案后若已有章节向量，可重建 HNSW 索引以优化检索。</span>
        <el-button size="small" :loading="rebuildingIndex" @click="handleRebuildIndex">
          重建 HNSW 索引
        </el-button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.embedding-section {
  scroll-margin-top: 72px;
}

.head-badge {
  flex-shrink: 0;
  margin-left: auto;
  padding-right: 4px;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.status-pill.ok {
  background: rgba(34, 197, 94, 0.12);
  color: #15803d;
}

.status-pill.warn {
  background: rgba(245, 158, 11, 0.14);
  color: #b45309;
}

.status-pill.muted {
  background: var(--color-bg-hover);
  color: var(--color-text-muted);
}

.tone-ok {
  color: #15803d;
}

.tone-warn {
  color: #b45309;
}

.tone-muted {
  color: var(--color-text-muted);
}

.emb-alert {
  margin-bottom: 4px;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

@media (max-width: 720px) {
  .status-grid {
    grid-template-columns: 1fr;
  }
}

.status-cell {
  padding: 12px 14px;
  background: var(--color-bg-surface-muted);
  border: 1px solid #e8edf3;
  border-radius: 10px;
}

.cell-label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-subtle);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 4px;
}

.cell-value {
  font-size: 14px;
  font-weight: 700;
  color: var(--color-text-strong);
}

.cell-value.ok {
  color: #15803d;
}

.cell-value.warn {
  color: #b45309;
}

.section-label {
  margin: 18px 0 10px;
  font-size: 12px;
  font-weight: 700;
  color: var(--color-text-muted);
}

.mode-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

@media (max-width: 640px) {
  .mode-grid {
    grid-template-columns: 1fr;
  }
}

.mode-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  padding: 14px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-bg-surface);
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
  text-align: left;
}

.mode-card:hover {
  border-color: var(--color-border);
}

.mode-card.active {
  border-color: var(--primary, #c66f4f);
  box-shadow: 0 0 0 1px rgba(198, 111, 79, 0.25);
  background: var(--color-primary-soft);
}

.mode-icon {
  font-size: 22px;
  margin-bottom: 2px;
}

.mode-icon.local {
  color: var(--color-primary-hover);
}

.mode-icon.cloud {
  color: var(--color-success);
}

.mode-icon.stub {
  color: var(--color-warning);
}

.mode-title {
  font-size: 14px;
  font-weight: 800;
  color: var(--color-text-strong);
}

.mode-desc {
  font-size: 12px;
  color: var(--color-text-muted);
}

.mode-panel {
  margin-top: 14px;
  padding: 18px;
  border: 1px solid #e8edf3;
  border-radius: 12px;
  background: var(--color-bg-surface-muted);
}

.panel-intro {
  margin-bottom: 14px;
  padding: 12px 14px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.55;
  color: var(--color-text-muted);
}

.panel-intro.local {
  background: rgba(37, 99, 235, 0.06);
  border: 1px solid rgba(37, 99, 235, 0.12);
}

.panel-intro.cloud {
  background: rgba(5, 150, 105, 0.06);
  border: 1px solid rgba(5, 150, 105, 0.12);
}

.panel-intro.stub {
  background: rgba(245, 158, 11, 0.06);
  border: 1px solid rgba(245, 158, 11, 0.15);
}

.panel-intro p {
  margin: 0;
}

.dep-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.dep-chip {
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  color: var(--color-text-muted);
}

.dep-chip.ok {
  border-color: rgba(34, 197, 94, 0.35);
  color: #15803d;
  background: rgba(34, 197, 94, 0.08);
}

.panel-action {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
}

.panel-action.center {
  align-items: center;
}

.panel-action.end {
  align-items: flex-end;
}

.running-text {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
}

.fail-hint {
  margin: 0;
  font-size: 12px;
  color: var(--color-danger);
}

.done-banner {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 14px;
  width: 100%;
  background: rgba(34, 197, 94, 0.08);
  border: 1px solid rgba(34, 197, 94, 0.2);
  border-radius: 10px;
  color: #15803d;
}

.done-banner .el-icon {
  font-size: 22px;
  flex-shrink: 0;
  margin-top: 2px;
}

.done-banner strong {
  display: block;
  font-size: 14px;
  margin-bottom: 4px;
}

.done-banner p {
  margin: 0;
  font-size: 12px;
  color: #047857;
}

.cloud-form {
  width: 100%;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

@media (max-width: 560px) {
  .form-row {
    grid-template-columns: 1fr;
  }
}

.tools-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px dashed var(--color-border);
}

.tools-hint {
  font-size: 12px;
  color: var(--color-text-subtle);
  line-height: 1.5;
  max-width: 420px;
}

.preset-label {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 700;
  color: var(--color-text-muted);
}

.preset-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 14px;
}

.preset-chip {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: 10px 14px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  background: var(--color-bg-surface);
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.preset-chip:hover {
  border-color: var(--color-border);
}

.preset-chip.active {
  border-color: var(--primary, #c66f4f);
  box-shadow: 0 0 0 1px rgba(198, 111, 79, 0.2);
  background: var(--color-primary-soft);
}

.preset-name {
  font-size: 13px;
  font-weight: 800;
  color: var(--color-text-strong);
}

.preset-model {
  font-size: 11px;
  color: var(--color-text-muted);
}

.endpoint-hint {
  margin: -4px 0 12px;
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.5;
}
</style>
