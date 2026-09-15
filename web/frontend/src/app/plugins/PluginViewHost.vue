<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Loading, Warning } from '@element-plus/icons-vue'

import { closePluginViewSession, createPluginViewSession, fetchPluginViewDocument } from '../../api'
import { usePluginNavigationStore } from '../../stores/pluginNavigation'
import { useTheme } from '../../composables/useTheme'
import { PluginRpcBridge } from './pluginRpc'
import { wrapPluginViewHtml } from './pluginViewDocument'

const props = defineProps<{
  pluginId: string
  viewId: string
  surface: 'library_sidebar' | 'project_sidebar'
  projectId?: string
}>()

const pluginNav = usePluginNavigationStore()
const { resolvedTheme } = useTheme()

const iframeRef = ref<HTMLIFrameElement | null>(null)
const loading = ref(true)
const error = ref<string | null>(null)
const sessionId = ref<string | null>(null)
const missingDocument = ref(false)
const viewTitle = ref('')
const sessionGeneration = ref(0)

let bridge: PluginRpcBridge | null = null

function getThemeTokens() {
  const isDark = document.documentElement.classList.contains('dark')
  const style = getComputedStyle(document.documentElement)
  return {
    isDark,
    primaryColor: style.getPropertyValue('--color-primary').trim() || (isDark ? '#d4845f' : '#c66f4f'),
    bgApp: style.getPropertyValue('--color-bg-app').trim() || (isDark ? '#0c1118' : '#f6f4f1'),
    bgSurface: style.getPropertyValue('--color-bg-surface').trim() || (isDark ? '#141b24' : '#ffffff'),
    bgCard: style.getPropertyValue('--color-bg-surface').trim() || (isDark ? '#141b24' : '#ffffff'),
    textPrimary: style.getPropertyValue('--color-text').trim() || (isDark ? '#e2e8f0' : '#1f2937'),
    textMuted: style.getPropertyValue('--color-text-muted').trim() || (isDark ? '#94a3b8' : '#697386'),
    border: style.getPropertyValue('--color-border').trim() || (isDark ? '#2a3646' : '#e1e7ef'),
  }
}

async function teardownSession(reason: 'project_change' | 'navigation' | 'user_close' = 'navigation') {
  if (bridge) {
    try {
      await bridge.sendDispose(reason, 2000)
    } catch {
      // ignore
    }
    bridge.destroy()
    bridge = null
  }
  if (sessionId.value) {
    const sid = sessionId.value
    sessionId.value = null
    try {
      await closePluginViewSession(props.pluginId, props.viewId, sid)
    } catch {
      // ignore
    }
  }
}

async function startSession() {
  const generation = ++sessionGeneration.value
  loading.value = true
  error.value = null
  missingDocument.value = false
  viewTitle.value = ''

  try {
    const effectiveProjectId = props.surface === 'project_sidebar' ? props.projectId : undefined
    const res = await createPluginViewSession(
      props.pluginId,
      props.viewId,
      effectiveProjectId,
      pluginNav.contextRevision,
    )
    if (generation !== sessionGeneration.value) {
      try {
        await closePluginViewSession(props.pluginId, props.viewId, res.data.session_id)
      } catch {
        /* ignore stale session */
      }
      return
    }
    sessionId.value = res.data.session_id
    const document = await fetchPluginViewDocument(props.pluginId, props.viewId, res.data.session_id)
    if (generation !== sessionGeneration.value) {
      try {
        await closePluginViewSession(props.pluginId, props.viewId, res.data.session_id)
      } catch {
        /* ignore stale session */
      }
      return
    }
    viewTitle.value = document.data.title || props.viewId
    if (!document.data.has_document || !document.data.html.trim()) {
      missingDocument.value = true
      loading.value = false
      return
    }

    await nextTick()
    if (generation !== sessionGeneration.value) {
      try {
        await closePluginViewSession(props.pluginId, props.viewId, res.data.session_id)
      } catch {
        /* ignore stale session */
      }
      return
    }
    if (!iframeRef.value) {
      throw new Error('Iframe container mount failed')
    }

    bridge = new PluginRpcBridge({
      iframe: iframeRef.value,
      pluginId: props.pluginId,
      viewId: props.viewId,
      sessionId: sessionId.value!,
      contextRevision: pluginNav.contextRevision,
    })

    bridge.onReady = () => {
      if (generation !== sessionGeneration.value) return
      bridge?.sendInit({
        projectId: props.projectId,
        surface: props.surface,
        theme: getThemeTokens(),
      })
      loading.value = false
    }

    iframeRef.value.srcdoc = wrapPluginViewHtml(document.data.html)
  } catch (err: any) {
    if (generation !== sessionGeneration.value) return
    error.value = err?.response?.data?.detail || err?.message || '无法初始化插件视图会话'
    loading.value = false
  }
}

async function retrySession() {
  sessionGeneration.value += 1
  await teardownSession('user_close')
  await startSession()
}

watch(
  () => [props.pluginId, props.viewId, props.projectId],
  async () => {
    pluginNav.incrementRevision()
    sessionGeneration.value += 1
    await teardownSession('project_change')
    await startSession()
  },
)

watch(resolvedTheme, () => {
  if (bridge) {
    bridge.sendTheme(getThemeTokens())
  }
})

onMounted(() => {
  void startSession()
})

onBeforeUnmount(() => {
  sessionGeneration.value += 1
  void teardownSession('navigation')
})
</script>

<template>
  <div class="plugin-view-host">
    <div v-if="error" class="host-error">
      <el-icon class="error-icon"><Warning /></el-icon>
      <h4>视图加载受阻</h4>
      <p>{{ error }}</p>
      <el-button type="primary" size="small" @click="retrySession">重试</el-button>
    </div>

    <div v-else-if="missingDocument" class="host-empty">
      <el-icon class="empty-icon"><Warning /></el-icon>
      <h4>{{ viewTitle || '插件视图' }}</h4>
      <p>该插件已启用，但没有提供可嵌入的视图页面。请在清单的 navigation.html 中声明插件目录内的 .html 文件。</p>
    </div>

    <div v-else class="host-frame-wrapper">
      <div v-if="loading" class="host-loading">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>正在加载插件视图…</span>
      </div>
      <iframe
        ref="iframeRef"
        class="plugin-sandboxed-iframe"
        sandbox="allow-scripts allow-forms allow-modals"
        title="Plugin view"
      />
    </div>
  </div>
</template>

<style scoped>
.plugin-view-host {
  width: 100%;
  height: 100%;
  min-height: 100%;
  position: relative;
  display: flex;
  flex-direction: column;
  flex: 1;
  background: var(--color-bg-app);
}

.host-frame-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  flex: 1;
  display: flex;
  background: var(--color-bg-app);
}

.host-loading {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  background: var(--color-bg-app);
  color: var(--color-text-muted);
  font-size: 14px;
  z-index: 2;
}

.host-loading .el-icon {
  font-size: 28px;
  color: var(--color-primary);
}

.plugin-sandboxed-iframe {
  width: 100%;
  height: 100%;
  min-height: 100%;
  border: none;
  background: var(--color-bg-app);
  flex: 1;
}

.host-error,
.host-empty {
  padding: 48px 24px;
  text-align: center;
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
}

.host-empty h4,
.host-error h4 {
  margin: 12px 0 8px;
}

.host-empty p {
  margin: 0 auto;
  max-width: 36em;
  color: var(--color-text-muted);
  line-height: 1.6;
}

.empty-icon {
  font-size: 40px;
  color: var(--color-text-muted);
}

.error-icon {
  font-size: 40px;
  color: var(--color-warning, #e6a23c);
  margin-bottom: 12px;
}

.host-error h4 {
  margin: 0 0 8px;
  color: var(--color-text-primary);
  font-size: 16px;
}

.host-error p {
  margin: 0 0 20px;
  color: var(--color-text-muted);
  font-size: 13.5px;
}
</style>
