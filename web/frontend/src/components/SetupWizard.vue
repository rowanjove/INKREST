<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElNotification } from 'element-plus'
import api, { getEmbeddingStatus, startSetupLocal, getSetupLocalStatus, updateConfig } from '../api'
import { resolveEmbeddingCloudEndpoint } from '../constants/embeddingPresets'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'completed'): void
}>()

const activeTab = ref<'local' | 'cloud' | 'stub'>('local')
const checkingStatus = ref(false)
const testingCloud = ref(false)
const envStatus = ref({
  has_onnx: false,
  has_transformers: false,
  has_model: false,
  provider: 'stub',
  model_path: null as string | null
})

// Local download & install state
const setupState = ref({
  status: 'idle', // 'idle', 'running', 'completed', 'failed'
  step: '',
  progress: 0,
  message: '',
  error: null as string | null
})

let statusTimer: number | null = null

// Cloud configuration fields
const cloudForm = ref({
  provider: 'zhipu', // 'zhipu' or 'openai'
  base_url: 'https://api.openai.com/v1',
  api_key: '',
  model: 'text-embedding-3-small'
})

const fetchStatus = async () => {
  checkingStatus.value = true
  try {
    const { data } = await getEmbeddingStatus()
    envStatus.value = data
    if (data.provider === 'local') activeTab.value = 'local'
    else if (
      data.provider === 'openai' ||
      data.provider === 'zhipu' ||
      data.provider === 'dashscope' ||
      data.provider === 'bailian'
    ) {
      activeTab.value = 'cloud'
    }
    else activeTab.value = 'stub'
  } catch (e: any) {
    console.error('获取向量检索状态失败', e)
  } finally {
    checkingStatus.value = false
  }
}

// Start polling backend setup progress
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
          title: '部署完成',
          message: '本地依赖与 BGE 向量模型部署成功！已自动开启本地嵌入向量检索。',
          type: 'success',
          duration: 5000
        })
        await fetchStatus()
        emit('completed')
      } else if (data.status === 'failed') {
        window.clearInterval(statusTimer!)
        statusTimer = null
        ElMessage.error(`本地环境部署失败: ${data.error || '未知错误'}`)
      }
    } catch (e: any) {
      console.error('获取安装进度失败', e)
    }
  }, 1000)
}

// Select Local Deployment Option
const handleLocalDeploy = async () => {
  try {
    const { data } = await startSetupLocal()
    if (data.status === 'started' || data.status === 'already_running') {
      setupState.value.status = 'running'
      setupState.value.progress = 5
      setupState.value.message = '正在请求后端启动部署进程...'
      startPollingStatus()
    }
  } catch (e: any) {
    ElMessage.error('无法启动部署进程: ' + e.message)
  }
}

// Select Cloud Configuration Option
const handleCloudSave = async () => {
  if (!cloudForm.value.api_key.trim()) {
    ElMessage.warning('请输入您的 API Key')
    return
  }
  
  testingCloud.value = true
  try {
    const { base_url, model } = resolveEmbeddingCloudEndpoint(
      cloudForm.value.provider,
      cloudForm.value.base_url,
      cloudForm.value.model,
    )
    
    // 1. Test connection
    const testResp = await api.post('/config/embedding/test', {
      provider: cloudForm.value.provider,
      base_url: base_url,
      api_key: cloudForm.value.api_key.trim(),
      model: model
    })
    
    if (!testResp.data.success) {
      ElMessage.error('云端接口测试失败: ' + testResp.data.error)
      return
    }
    
    // 2. Save configuration
    await updateConfig({
      embedding: {
        provider: cloudForm.value.provider,
        base_url: base_url,
        api_key: cloudForm.value.api_key.trim(),
        model: model
      }
    })
    
    ElMessage.success('云端 API 配置成功，连接通道正常！')
    await fetchStatus()
    emit('completed')
  } catch (e: any) {
    ElMessage.error('云端配置保存失败: ' + e.message)
  } finally {
    testingCloud.value = false
  }
}

// Select Stub Option
const handleSkipSetup = async () => {
  try {
    await updateConfig({
      embedding: {
        provider: 'stub'
      }
    })
    ElMessage.info('已选择跳过。系统将使用基于关键词的传统分词匹配。')
    await fetchStatus()
    emit('completed')
  } catch (e: any) {
    ElMessage.error('保存设置失败: ' + e.message)
  }
}

const handleClose = () => {
  if (setupState.value.status === 'running') {
    ElMessage.warning('本地环境部署正在后台运行，您可以关闭对话框，它会继续在后台下载。')
  }
  emit('close')
}

onMounted(() => {
  fetchStatus()
  // Check if setup is already running
  getSetupLocalStatus()
    .then(({ data }) => {
      setupState.value = data
      if (data.status === 'running') {
        startPollingStatus()
      }
    })
    .catch((e) => {
      console.error('获取本地安装状态失败:', e)
    })
})

onBeforeUnmount(() => {
  if (statusTimer) window.clearInterval(statusTimer)
})
</script>

<template>
  <el-dialog
    v-model="props.visible"
    title="🤖 小说生成 Agent — AI 模型配置向导"
    width="680px"
    :before-close="handleClose"
    :close-on-click-modal="false"
    append-to-body
    custom-class="setup-wizard-dialog"
  >
    <div class="wizard-container" v-loading="checkingStatus">
      <div class="wizard-intro-header">
        <p class="subtitle">
          为了能够对您创作的章节历史进行<strong>语义智能关联</strong>与<strong>大纲伏笔诊断</strong>，系统需要建立向量数据库。您可以根据设备和网络情况选择以下三种向量模型配置方案：
        </p>
      </div>

      <!-- Tab Buttons -->
      <div class="wizard-tabs">
        <div 
          class="tab-btn" 
          :class="{ active: activeTab === 'local' }"
          @click="activeTab = 'local'"
        >
          <span class="tab-icon">💻</span>
          <div class="tab-meta">
            <span class="tab-title">本地部署 (ONNX)</span>
            <span class="tab-desc">完全离线，保障隐私</span>
          </div>
        </div>

        <div 
          class="tab-btn" 
          :class="{ active: activeTab === 'cloud' }"
          @click="activeTab = 'cloud'"
        >
          <span class="tab-icon">☁️</span>
          <div class="tab-meta">
            <span class="tab-title">云端 API 连接</span>
            <span class="tab-desc">零内存占用，连接极速</span>
          </div>
        </div>

        <div 
          class="tab-btn" 
          :class="{ active: activeTab === 'stub' }"
          @click="activeTab = 'stub'"
        >
          <span class="tab-icon">⏳</span>
          <div class="tab-meta">
            <span class="tab-title">暂不配置 (Stub)</span>
            <span class="tab-desc">词频匹配，无需网络/显卡</span>
          </div>
        </div>
      </div>

      <!-- Tab Content Area -->
      <div class="tab-content-panel">
        
        <!-- LOCAL PANEL -->
        <div v-if="activeTab === 'local'" class="panel-section">
          <div class="banner-info local-banner">
            <div class="banner-title">💻 本地 BGE-Micro 向量嵌入引擎</div>
            <p>
              主程序分发包排除了庞大的 AI 模型和运行库（以控制在 50MB 以内）。选择此项，系统将<b>一键自动下载并配置 BGE 向量模型</b> (~45MB) 并补齐必要的 Python 库 (onnxruntime, transformers)。
            </p>
            <ul class="advantage-list">
              <li>✨ <strong>完全离线</strong>: 所有的分析与检索均在本地电脑处理，绝对保障大纲与稿件安全。</li>
              <li>🚀 <strong>极速响应</strong>: 微型量化模型在普通 CPU 即可实现毫秒级向量生成，不消耗云端额度。</li>
            </ul>
          </div>

          <div class="status-summary-bar">
            <div class="status-item">
              <span class="dot" :class="{ green: envStatus.has_onnx && envStatus.has_transformers }"></span>
              <span>Python 算法环境: <strong>{{ (envStatus.has_onnx && envStatus.has_transformers) ? '已就绪' : '未就绪' }}</strong></span>
            </div>
            <div class="status-item">
              <span class="dot" :class="{ green: envStatus.has_model }"></span>
              <span>BGE ONNX 向量模型: <strong>{{ envStatus.has_model ? '已安装' : '未下载' }}</strong></span>
            </div>
          </div>

          <!-- Deploy Control -->
          <div class="deploy-control-box">
            <!-- Idle / Not started -->
            <div v-if="setupState.status === 'idle' || setupState.status === 'failed'" class="setup-trigger">
              <el-button 
                type="primary" 
                size="large"
                class="gradient-action-btn"
                @click="handleLocalDeploy"
              >
                📥 一键下载并部署本地 AI 引擎
              </el-button>
              <p class="btn-subtext" v-if="setupState.status === 'failed'">
                ❌ 上次部署失败: {{ setupState.error }}
              </p>
            </div>

            <!-- Running -->
            <div v-else-if="setupState.status === 'running'" class="setup-running">
              <div class="running-info">
                <span class="spinner">⏳</span>
                <span>{{ setupState.message }}</span>
              </div>
              <el-progress 
                :percentage="setupState.progress" 
                :stroke-width="12"
                striped 
                striped-flow 
                class="wizard-progress"
              />
              <p class="running-tips">系统正在本地为您构建隔离环境并拉取模型，这不会干扰您的网络浏览，完成后会自动启用。</p>
            </div>

            <!-- Completed -->
            <div v-else-if="setupState.status === 'completed' || envStatus.has_model" class="setup-completed">
              <div class="success-message">
                <span class="success-icon">✓</span>
                <div>
                  <h4>本地 AI 向量环境已配置就绪！</h4>
                  <p>当前系统正在使用本地 CPU BGE-Micro 进行高效语义库关联。</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- CLOUD PANEL -->
        <div v-if="activeTab === 'cloud'" class="panel-section">
          <div class="banner-info cloud-banner">
            <div class="banner-title">☁️ 接入云端大模型向量接口</div>
            <p>
              使用主流的在线大模型向量 API。计算全部在云端进行，不需要您的电脑安装任何重型推理包，极其节省内存与显存。
            </p>
          </div>

          <el-form label-position="top" class="cloud-setup-form">
            <div class="form-row">
              <el-form-item label="服务商 (Provider)" style="flex: 1;">
                <el-select v-model="cloudForm.provider" placeholder="请选择服务商" style="width: 100%;">
                  <el-option label="智谱 AI (text-embedding-3)" value="zhipu" />
                  <el-option label="阿里百炼 DashScope (text-embedding-v3)" value="dashscope" />
                  <el-option label="OpenAI 兼容平台" value="openai" />
                </el-select>
              </el-form-item>
              
              <el-form-item
                v-if="cloudForm.provider === 'openai' || cloudForm.provider === 'dashscope'"
                label="模型名称 (Model)"
                style="flex: 1;"
              >
                <el-input
                  v-model="cloudForm.model"
                  :placeholder="cloudForm.provider === 'dashscope' ? 'text-embedding-v3' : 'text-embedding-3-small'"
                />
              </el-form-item>
            </div>

            <el-form-item v-if="cloudForm.provider === 'openai'" label="接口地址 (Base URL)">
              <el-input v-model="cloudForm.base_url" placeholder="https://api.openai.com/v1" />
            </el-form-item>

            <el-form-item label="大模型密钥 API Key">
              <el-input 
                v-model="cloudForm.api_key" 
                type="password" 
                show-password 
                placeholder="请输入您的 API Key (如 sk-...)" 
              />
            </el-form-item>
          </el-form>

          <div style="display: flex; justify-content: flex-end; gap: 12px; margin-top: 20px;">
            <el-button 
              type="success" 
              size="large"
              :loading="testingCloud"
              class="cloud-save-btn"
              @click="handleCloudSave"
            >
              ⚡️ 测试连接并保存
            </el-button>
          </div>
        </div>

        <!-- STUB PANEL -->
        <div v-if="activeTab === 'stub'" class="panel-section">
          <div class="banner-info stub-banner">
            <div class="banner-title">⏳ 暂不配置 (使用传统关键词 Stub 匹配)</div>
            <p>
              如果您目前在旅途中、网络不稳定，或者不想进行任何配置，可以选择此项。
            </p>
            <ul class="advantage-list">
              <li>✨ <strong>零依赖</strong>: 使用自带的正则表达式或中文分词，不需要安装任何 AI 算法库。</li>
              <li>💬 <strong>核心功能正常</strong>: 写作、AI 润色、新建章节依然完全可用，仅资产库自动检索精确度略受限。</li>
            </ul>
          </div>

          <div style="display: flex; justify-content: center; margin-top: 30px; margin-bottom: 10px;">
            <el-button 
              type="warning" 
              size="large"
              class="stub-action-btn"
              @click="handleSkipSetup"
            >
              ⚙️ 确认并使用关键词匹配 (Stub)
            </el-button>
          </div>
        </div>

      </div>
    </div>
  </el-dialog>
</template>

<style scoped>
.wizard-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 4px 8px;
}
.wizard-intro-header .subtitle {
  font-size: 13.5px;
  line-height: 1.6;
  color: var(--color-text-muted);
  margin: 0 0 10px;
}
.wizard-intro-header strong {
  color: var(--color-text-strong);
}

/* Custom Tabs styling */
.wizard-tabs {
  display: flex;
  gap: 12px;
  margin-bottom: 8px;
}
.tab-btn {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  background: var(--color-bg-surface-muted);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  user-select: none;
}
.tab-btn:hover {
  background: var(--color-bg-hover);
  border-color: var(--color-border);
}
.tab-btn.active {
  background: var(--color-bg-surface);
  border-color: var(--color-primary);
  box-shadow: 0 4px 16px var(--color-primary-muted);
}
.tab-icon {
  font-size: 24px;
}
.tab-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.tab-title {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--color-text-strong);
}
.tab-btn.active .tab-title {
  color: var(--color-primary);
}
.tab-desc {
  font-size: 10px;
  color: var(--color-text-muted);
}

/* Panel content */
.tab-content-panel {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-subtle);
  border-radius: 12px;
  padding: 20px;
  min-height: 280px;
}
.banner-info {
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 16px;
  font-size: 13px;
  line-height: 1.6;
}
.banner-title {
  font-size: 14.5px;
  font-weight: 800;
  margin-bottom: 8px;
}
.local-banner {
  background: rgba(59, 130, 246, 0.04);
  border: 1px solid rgba(59, 130, 246, 0.15);
  color: #1e3a8a;
}
.local-banner .banner-title {
  color: var(--color-primary-hover);
}
.cloud-banner {
  background: rgba(16, 185, 129, 0.04);
  border: 1px solid rgba(16, 185, 129, 0.15);
  color: #065f46;
}
.cloud-banner .banner-title {
  color: var(--color-success);
}
.stub-banner {
  background: rgba(245, 158, 11, 0.04);
  border: 1px solid rgba(245, 158, 11, 0.15);
  color: #78350f;
}
.stub-banner .banner-title {
  color: var(--color-warning);
}
.advantage-list {
  margin: 10px 0 0 0;
  padding-left: 20px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.advantage-list li {
  list-style-type: disc;
}

/* Status bar */
.status-summary-bar {
  display: flex;
  gap: 20px;
  background: var(--color-bg-surface-muted);
  padding: 10px 16px;
  border-radius: 8px;
  margin-bottom: 20px;
}
.status-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--color-text-muted);
}
.status-item .dot {
  width: 8px;
  height: 8px;
  background: var(--color-border);
  border-radius: 50%;
}
.status-item .dot.green {
  background: var(--color-success);
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.6);
}

/* Deploy action area */
.deploy-control-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 0;
}
.gradient-action-btn {
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-hover)) !important;
  border: none !important;
  color: var(--color-bg-surface) !important;
  font-weight: 700 !important;
  padding: 12px 28px !important;
  border-radius: 8px !important;
  box-shadow: 0 4px 14px var(--color-primary-muted) !important;
  transition: all 0.2s !important;
}
.gradient-action-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px var(--color-primary-muted) !important;
}
.btn-subtext {
  font-size: 11px;
  color: var(--color-danger);
  margin-top: 8px;
  text-align: center;
}

.setup-running {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.running-info {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13.5px;
  font-weight: 700;
  color: var(--color-text);
}
.spinner {
  display: inline-block;
  animation: spin 2s linear infinite;
}
@keyframes spin {
  100% { transform: rotate(360deg); }
}
.wizard-progress {
  width: 100%;
}
.running-tips {
  font-size: 11px;
  color: var(--color-text-muted);
  margin: 0;
  line-height: 1.4;
}

.setup-completed {
  width: 100%;
}
.success-message {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  background: rgba(16, 185, 129, 0.08);
  border: 1px dashed rgba(16, 185, 129, 0.3);
  padding: 16px;
  border-radius: 8px;
}
.success-icon {
  width: 24px;
  height: 24px;
  background: var(--color-success);
  color: var(--color-bg-surface);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-weight: bold;
  flex-shrink: 0;
}
.success-message h4 {
  margin: 0 0 4px 0;
  color: #065f46;
  font-size: 14px;
  font-weight: 700;
}
.success-message p {
  margin: 0;
  font-size: 12px;
  color: #047857;
}

/* Cloud Form */
.cloud-setup-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.form-row {
  display: flex;
  gap: 16px;
}
.cloud-save-btn {
  background: linear-gradient(135deg, var(--color-success), var(--color-success)) !important;
  border: none !important;
  color: var(--color-bg-surface) !important;
  font-weight: 700 !important;
  box-shadow: 0 4px 14px rgba(16, 185, 129, 0.3) !important;
}
.cloud-save-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(16, 185, 129, 0.45) !important;
}

/* Stub Form button */
.stub-action-btn {
  background: linear-gradient(135deg, var(--color-warning), var(--color-warning)) !important;
  border: none !important;
  color: var(--color-bg-surface) !important;
  font-weight: 700 !important;
  box-shadow: 0 4px 14px rgba(245, 158, 11, 0.3) !important;
}
.stub-action-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(245, 158, 11, 0.45) !important;
}
</style>
