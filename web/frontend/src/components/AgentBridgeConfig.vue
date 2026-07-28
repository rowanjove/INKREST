<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CopyDocument, Connection, Document } from '@element-plus/icons-vue'
import {
  getAgentBridgeSettings,
  getAgentSnapshot,
  updateAgentBridgeSettings,
} from '../api'

type McpMode = 'auto' | 'offline' | 'http'

const route = useRoute()
const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const expanded = ref(false)

const openFromHash = () => {
  const h = (route.hash || '').replace(/^#/, '')
  if (h === 'agent-bridge') expanded.value = true
}

const mcpMode = ref<McpMode>('auto')
const apiUrlOverride = ref('')
const showHints = ref(true)
const accessToken = ref('')

const integration = ref<Record<string, any>>({})
const snapshotPreview = ref('')

const mcpInstalled = computed(() => Boolean(integration.value?.mcp_installed))
const effectiveApiUrl = computed(() => {
  const o = apiUrlOverride.value.trim()
  return o || 'http://127.0.0.1:8000'
})

const load = async () => {
  loading.value = true
  try {
    const { data } = await getAgentBridgeSettings()
    const s = data.settings || {}
    mcpMode.value = (s.mcp_mode as McpMode) || 'auto'
    apiUrlOverride.value = s.api_url_override || ''
    showHints.value = s.show_integration_hints !== false
    integration.value = data.integration || {}
    accessToken.value = window.localStorage.getItem('novel-agent-access-token') || ''
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const save = async () => {
  saving.value = true
  try {
    const { data } = await updateAgentBridgeSettings({
      mcp_mode: mcpMode.value,
      api_url_override: apiUrlOverride.value.trim(),
      show_integration_hints: showHints.value,
    })
    integration.value = data.integration || integration.value
    const t = accessToken.value.trim()
    if (t) {
      window.localStorage.setItem('novel-agent-access-token', t)
    } else {
      window.localStorage.removeItem('novel-agent-access-token')
    }
    ElMessage.success('Agent 接入设置已保存')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const copyText = async (text: string, label: string) => {
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success(`已复制：${label}`)
  } catch {
    ElMessage.warning('复制失败，请手动选中复制')
  }
}

const testSnapshot = async () => {
  testing.value = true
  snapshotPreview.value = ''
  try {
    const { data } = await getAgentSnapshot()
    snapshotPreview.value = JSON.stringify(data, null, 2)
    ElMessage.success('快照拉取成功（见下方预览）')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error.message || '快照失败')
  } finally {
    testing.value = false
  }
}

onMounted(() => {
  openFromHash()
  load()
})
watch(() => route.hash, openFromHash)
</script>

<template>
  <section id="agent-bridge" class="fold-card agent-bridge-section" v-loading="loading">
    <div class="fold-head" @click="expanded = !expanded">
      <div class="head-left">
        <span class="collapse-arrow" :class="{ open: expanded }">▶</span>
        <div>
          <h2>AI Agent 接入</h2>
          <p>供 Cursor / Grok / CLI 查询全书状态与日志（只读）。</p>
        </div>
      </div>
      <el-tag v-if="mcpInstalled" type="success" size="small">MCP 已安装</el-tag>
      <el-tag v-else type="info" size="small">MCP 未安装（可选）</el-tag>
    </div>

    <div v-show="expanded" class="fold-body">
      <div class="form-grid">
        <label class="field">
          <span class="label">外部 API 地址</span>
          <el-input
            v-model="apiUrlOverride"
            placeholder="http://127.0.0.1:8000（留空用默认）"
            clearable
          />
          <span class="hint">留空默认本机 8000 端口</span>
        </label>

        <label class="field">
          <span class="label">MCP 连接模式</span>
          <el-select v-model="mcpMode" style="width: 100%">
            <el-option value="auto" label="自动（能连 API 则用 HTTP）" />
            <el-option value="offline" label="离线（只读磁盘）" />
            <el-option value="http" label="始终 HTTP" />
          </el-select>
        </label>

        <label class="field span-2">
          <span class="label">客户端访问令牌</span>
          <el-input
            v-model="accessToken"
            type="password"
            show-password
            placeholder="与 NOVEL_AGENT_ACCESS_TOKEN 一致（存于本浏览器）"
            clearable
          />
          <span class="hint">
            与 <code>NOVEL_AGENT_ACCESS_TOKEN</code> 一致；留空不鉴权
            <template v-if="integration.access_token_env_set"> · 服务端已配置</template>
          </span>
        </label>

        <label class="field checkbox-row span-2">
          <el-checkbox v-model="showHints">在文档区显示接入提示</el-checkbox>
        </label>
      </div>

      <div class="actions-row">
        <el-button type="primary" :loading="saving" @click="save">保存接入设置</el-button>
        <el-button :loading="testing" @click="testSnapshot">
          <el-icon><Connection /></el-icon>
          测试快照 API
        </el-button>
      </div>

      <div class="kit-section">
        <h3>快速复制</h3>
        <div class="kit-buttons">
          <el-button
            size="small"
            @click="copyText(integration.mcp_config_text || '', 'MCP 配置')"
          >
            <el-icon><CopyDocument /></el-icon>
            MCP 配置（Cursor）
          </el-button>
          <el-button
            size="small"
            @click="copyText((integration.cli_examples || [])[0] || '', 'CLI 命令')"
          >
            <el-icon><CopyDocument /></el-icon>
            CLI · 项目列表
          </el-button>
          <el-button
            size="small"
            @click="copyText((integration.cli_examples || [])[1] || '', 'CLI 快照')"
          >
            <el-icon><CopyDocument /></el-icon>
            CLI · 状态快照
          </el-button>
          <el-button
            size="small"
            @click="
              copyText(
                `NOVEL_AGENT_ROOT=${integration.workspace_root}\nNOVEL_AGENT_API_URL=${effectiveApiUrl}`,
                '环境变量',
              )
            "
          >
            <el-icon><Document /></el-icon>
            环境变量
          </el-button>
        </div>
        <p v-if="!mcpInstalled" class="install-hint">
          需要 MCP 时执行：<code>{{ integration.mcp_install_hint }}</code>
        </p>
      </div>

      <details class="api-table-wrap">
        <summary>HTTP 端点（只读）</summary>
        <ul>
          <li v-for="ep in integration.api_endpoints || []" :key="ep">
            <code>{{ ep }}</code>
          </li>
        </ul>
      </details>

      <details v-if="showHints" class="doc-links">
        <summary>说明文档</summary>
        <p>
          仓库内
          <code>{{ integration.docs_relative }}</code>
          · Skill
          <code>{{ integration.skill_relative }}</code>
        </p>
        <p class="cli-list">
          <span v-for="(cmd, i) in integration.cli_examples || []" :key="i" class="cli-line">
            <code>{{ cmd }}</code>
          </span>
        </p>
      </details>

      <pre v-if="snapshotPreview" class="snapshot-preview">{{ snapshotPreview }}</pre>
    </div>
  </section>
</template>

<style scoped>
.agent-bridge-section {
  scroll-margin-top: 72px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px 16px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field .label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-strong);
}

.field .hint {
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.45;
}

.span-2 {
  grid-column: 1 / -1;
}

.checkbox-row {
  flex-direction: row;
  align-items: center;
}

.actions-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.kit-section h3 {
  margin: 0 0 8px;
  font-size: 14px;
  font-weight: 700;
}

.kit-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.install-hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--color-text-muted);
}

.api-table-wrap,
.doc-links {
  font-size: 13px;
  color: var(--color-text-muted);
}

.api-table-wrap ul {
  margin: 8px 0 0;
  padding-left: 20px;
}

.cli-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 8px;
}

.cli-line code {
  display: block;
  padding: 6px 8px;
  border-radius: 6px;
  background: var(--color-bg-muted);
  font-size: 11px;
  word-break: break-all;
}

.snapshot-preview {
  max-height: 240px;
  overflow: auto;
  padding: 10px;
  border-radius: 8px;
  background: var(--color-bg-muted);
  font-size: 11px;
  line-height: 1.4;
}

@media (max-width: 720px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>