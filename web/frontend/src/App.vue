<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowRight,
  Collection,
  Cpu,
  DataLine,
  Document,
  Edit,
  Files,
  List,
  Monitor,
  Setting,
  MagicStick,
} from '@element-plus/icons-vue'
import { useProjectStore } from './stores/project'
import {
  getConfig,
  getEmbeddingStatus,
  getSystemReadiness,
  listAssets,
  listModels,
  listPrompts,
  listTasks,
} from './api'
import SetupWizard from './components/SetupWizard.vue'
import FirstBookGuide from './components/workbench/FirstBookGuide.vue'
import NovelBatchRunDialog from './components/NovelBatchRunDialog.vue'
import { provide } from 'vue'

const showSetupWizard = ref(false)
provide('openSetupWizard', () => {
  showSetupWizard.value = true
})

const handleWizardCompleted = () => {
  showSetupWizard.value = false
  localStorage.setItem('setup_wizard_completed', 'true')
  loadEngineStatus()
}

const route = useRoute()
const router = useRouter()
const projectStore = useProjectStore()
type EngineStage = { label: string; detail: string; ok: boolean; warn?: boolean }

const engineLabel = ref('检查中…')
const engineChecking = ref(true)
const engineReady = ref(false)
const engineWarn = ref(false)
const engineStages = ref<EngineStage[]>([])


let unlistenNavigate: (() => void) | null = null
const backendStatus = ref('online')
const backendUnreachable = ref(false)
let unlistenBackendStatus: (() => void) | null = null
let healthPollTimer: number | null = null
let healthFailStreak = 0
const HEALTH_FAIL_THRESHOLD = 2

const getHealthUrl = () => {
  const origin = window.location.origin
  if (origin.includes('tauri') || origin.startsWith('file:')) {
    return 'http://127.0.0.1:8000/api/health'
  }
  return `${origin}/api/health`
}

const checkBackendHealth = async () => {
  if (backendStatus.value === 'restarting') return
  try {
    const res = await fetch(getHealthUrl(), { signal: AbortSignal.timeout(8000) })
    if (!res.ok) throw new Error('health not ok')
    healthFailStreak = 0
    backendUnreachable.value = false
    if (backendStatus.value === 'offline') backendStatus.value = 'online'
  } catch {
    healthFailStreak += 1
    if (healthFailStreak >= HEALTH_FAIL_THRESHOLD) {
      backendUnreachable.value = true
      if (!window.electronAPI) backendStatus.value = 'offline'
    }
  }
}

onMounted(async () => {
  await projectStore.fetchCurrent()
  await loadEngineStatus()

  if (window.electronAPI?.onNavigate) {
    unlistenNavigate = window.electronAPI.onNavigate((routePath: string) => {
      router.push(routePath)
    })
  }

  if (window.electronAPI?.onBackendStatus) {
    unlistenBackendStatus = window.electronAPI.onBackendStatus((status: string) => {
      backendStatus.value = status
      backendUnreachable.value = status === 'offline'
    })
    window.electronAPI.getBackendStatus().then((status) => {
      backendStatus.value = status
      backendUnreachable.value = status === 'offline'
    })
  } else {
    void checkBackendHealth()
    healthPollTimer = window.setInterval(() => {
      void checkBackendHealth()
    }, 10_000)
  }
})

watch(
  () => projectStore.currentProject?.id,
  () => {
    void loadEngineStatus()
  },
)

watch(backendStatus, (status) => {
  if (status === 'online') {
    void loadEngineStatus()
  }
})

onBeforeUnmount(() => {
  if (unlistenNavigate) {
    unlistenNavigate()
  }
  if (unlistenBackendStatus) {
    unlistenBackendStatus()
  }
  if (healthPollTimer) {
    window.clearInterval(healthPollTimer)
    healthPollTimer = null
  }
})

const isInProject = computed(() => !!projectStore.currentProject?.id)

const menuItems = computed(() => {
  if (!isInProject.value) return []
  return [
    { path: '/workspace', label: '工作台', icon: DataLine },
    { path: '/outline', label: '大纲', icon: List },
    { path: '/chapters', label: '章节', icon: Document },
    { path: '/monitor', label: '日志中心', icon: Monitor },
    { path: '/writer', label: '写作', icon: Edit },
    { path: '/state', label: '状态库', icon: Collection },
    { path: '/assets', label: '项目资产', icon: Files },
  ]
})

const activePath = computed(() => {
  if (route.path.startsWith('/config')) return '/config'
  if (route.path.startsWith('/plugins')) return '/plugins'
  if (route.path.startsWith('/trope-workshop')) return '/trope-workshop'
  if (route.path.startsWith('/monitor')) return '/monitor'
  if (route.path === '/') return ''
  const match = menuItems.value.find((item) => item.path !== '/' && route.path.startsWith(item.path))
  return match?.path || ''
})

const isPetRoute = computed(() => route.path === '/pet' || route.path === '/pet-bubble')

const getStageRoute = (stage: EngineStage) => {
  const label = stage.label || ''
  if (label === '开书清单') return '/workspace'
  if (label === '插件安全') return '/plugins'
  if (label === '日常模型' || label === '语义向量' || label.includes('Agent') || label === '提示词') {
    return label === '语义向量' ? '/config#embedding-config' : '/config'
  }
  if (label === '项目资产') {
    return '/assets'
  }
  if (label === '任务队列') {
    return '/chapters/maintenance'
  }
  return null
}

const goToStage = (stage: EngineStage) => {
  const routePath = getStageRoute(stage)
  if (!routePath) return
  const hashIdx = routePath.indexOf('#')
  if (hashIdx >= 0) {
    const path = routePath.slice(0, hashIdx)
    const hash = routePath.slice(hashIdx + 1)
    router.push({ path, hash: `#${hash}` }).then(() => {
      requestAnimationFrame(() => {
        document.getElementById(hash)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      })
    })
    return
  }
  router.push(routePath)
}

const resolveEngine = (config: any, models: any[]) => {
  const llm = config?.llm || {}
  const modelsById = new Map(models.map((model: any) => [model.id, model]))
  const defaultId = llm.daily_model_id || llm.default_model_id || llm.default?.model_ref
  const defaultModel = defaultId ? modelsById.get(defaultId) : null
  if (defaultModel) {
    return { ready: true, label: defaultModel.name || defaultModel.id, model: defaultModel }
  }
  if (llm.default?.provider && llm.default.provider !== 'static') {
    return { ready: true, label: llm.default.model || llm.default.provider, model: null }
  }
  if (llm.provider && llm.provider !== 'static') {
    return { ready: true, label: llm.model || llm.provider, model: null }
  }
  return { ready: false, label: '未配置', model: null }
}

const embeddingStageDetail = (emb: {
  provider?: string
  vector_enabled?: boolean
  semantic_search_effective?: boolean
}) => {
  if (emb.vector_enabled === false) {
    return { detail: '当前体量未启用向量', ok: true, warn: false }
  }
  const provider = emb.provider || 'stub'
  if (emb.semantic_search_effective) {
    if (provider === 'local') return { detail: '本地 BGE 已生效', ok: true, warn: false }
    return { detail: `云端 ${provider} 已生效`, ok: true, warn: false }
  }
  if (provider === 'stub') {
    return { detail: '未配置（Stub，去重/召回不可用）', ok: false, warn: true }
  }
  return { detail: `${provider} 未就绪`, ok: false, warn: true }
}

const summarizeEngineLabel = (stages: EngineStage[], modelReady: boolean) => {
  const blocking = stages.filter((s) => !s.warn && !s.ok)
  const warnings = stages.filter((s) => s.warn && !s.ok)
  if (blocking.some((s) => s.label === '后端服务')) return '服务离线'
  if (!modelReady) return '待配置日常模型'
  if (blocking.length === 0 && warnings.length === 0) return '全部就绪'
  const okCount = stages.filter((s) => s.ok).length
  if (warnings.length > 0 && blocking.length === 0) {
    return `${okCount}/${stages.length} 就绪 · 向量待配置`
  }
  return `${okCount}/${stages.length} 项就绪`
}

const loadEngineStatus = async () => {
  engineChecking.value = true
  try {
    const [
      { data: config },
      { data: models },
      { data: prompts },
      { data: assets },
      tasksResp,
      embResp,
      readinessResp,
    ] = await Promise.all([
      getConfig(),
      listModels(),
      listPrompts(),
      listAssets(),
      listTasks().catch(() => ({ data: [] as any[] })),
      getEmbeddingStatus().catch(() => ({ data: {} as Record<string, unknown> })),
      getSystemReadiness().catch(() => ({ data: { checks: {} as Record<string, any> } })),
    ])
    const sysChecks = readinessResp.data?.checks || {}
    const tasks = tasksResp.data || []
    const emb = embResp.data || {}
    const engine = resolveEngine(config, models)
    const defaultModel = engine.model
    const nonEmptyPrompts = prompts.filter((item: any) => item.content?.trim()).length
    const failedTasks = tasks.filter((item: any) => item.status === 'failed').length
    const runningTasks = tasks.filter((item: any) => ['pending', 'running'].includes(item.status)).length
    const embStage = embeddingStageDetail(emb as Parameters<typeof embeddingStageDetail>[0])

    const configuredDefaultId =
      config.llm?.daily_model_id || config.llm?.default_model_id || config.llm?.default?.model_ref

    const llmCheck = sysChecks.llm
    const modelOk = llmCheck ? !!llmCheck.ok : engine.ready
    const modelDetail =
      llmCheck && !llmCheck.ok
        ? llmCheck.hint || '日常模型未就绪'
        : defaultModel
          ? defaultModel.name || defaultModel.id
          : configuredDefaultId
            ? `模型库中未找到 (${configuredDefaultId})`
            : '未设置日常档'

    const stages: EngineStage[] = []

    const pushCheck = (id: string, fallbackLabel: string) => {
      const c = sysChecks[id]
      if (!c || typeof c !== 'object') return
      stages.push({
        label: String(c.label || fallbackLabel),
        detail:
          c.hint ||
          (c.pending?.length ? `待办：${(c.pending as string[]).join('、')}` : '') ||
          (c.configured === false
            ? '未配置'
            : c.configured === true
              ? '已配置'
              : c.active
                ? '有任务运行中'
                : c.active === false
                  ? '空闲'
                  : c.enabled_count != null
                    ? `已启用 ${c.enabled_count} 个`
                    : c.ok
                      ? '正常'
                      : c.error || '需处理'),
        ok: c.ok !== false,
        warn: id === 'book' && !c.ok,
      })
    }

    pushCheck('api', 'API 服务')
    pushCheck('single_process', '单进程模式')
    pushCheck('remote_token', '远程访问令牌')

    if (sysChecks.llm) {
      stages.push({
        label: '日常模型',
        detail: modelDetail,
        ok: modelOk,
      })
    } else {
      stages.push({
        label: '日常模型',
        detail: modelDetail,
        ok: modelOk,
      })
    }

    const promptsAllFilled = prompts.length > 0 && nonEmptyPrompts === prompts.length
    const promptsPartial = prompts.length > 0 && nonEmptyPrompts > 0 && !promptsAllFilled
    stages.push(
      {
        label: '语义向量',
        detail: embStage.detail,
        ok: embStage.ok,
        warn: embStage.warn,
      },
      {
        label: '提示词',
        detail: prompts.length
          ? `${nonEmptyPrompts}/${prompts.length} 条已填写`
          : '尚无提示词模板',
        ok: promptsAllFilled,
        warn: promptsPartial || (prompts.length > 0 && nonEmptyPrompts === 0),
      },
    )

    if (isInProject.value) {
      pushCheck('book', '开书清单')
      stages.push({
        label: '项目资产',
        detail: assets.length ? `${assets.length} 个资产入口` : '尚无资产（可选）',
        ok: assets.length > 0,
        warn: assets.length === 0,
      })
      if (sysChecks.tasks) {
        pushCheck('tasks', '后台任务')
      } else {
        stages.push({
          label: '任务队列',
          detail: failedTasks
            ? `${failedTasks} 个失败任务`
            : runningTasks
              ? `${runningTasks} 个运行中`
              : '空闲',
          ok: failedTasks === 0,
        })
      }
    } else {
      pushCheck('book', '开书清单')
    }

    pushCheck('plugins', '插件')

    engineStages.value = stages
    const blocking = stages.some((s) => !s.ok && !s.warn)
    engineWarn.value = !blocking && stages.some((s) => !s.ok && s.warn)
    engineReady.value = !blocking
    engineLabel.value = summarizeEngineLabel(stages, modelOk)
  } catch {
    engineReady.value = false
    engineWarn.value = false
    engineLabel.value = '服务离线'
    engineStages.value = [{ label: '后端服务', detail: '无法连接，请检查后台进程', ok: false }]
  } finally {
    engineChecking.value = false
  }
}
</script>

<template>
  <router-view v-if="isPetRoute" />
  <div v-else class="app-shell" v-loading="backendStatus === 'restarting'" element-loading-text="后台服务异常中断，正在自动重启中，请稍候...">
    <el-alert
      v-if="backendStatus !== 'restarting' && (backendStatus === 'offline' || backendUnreachable)"
      class="backend-offline-alert"
      type="error"
      :closable="false"
      show-icon
      title="栖墨后台未响应"
      description="请重启应用或检查本地服务端口（默认 8000）。恢复连接后提示将自动消失。"
    />
    <aside class="sidebar">
      <button class="brand" @click="router.push('/')">
        <img src="/favicon.svg" alt="" class="brand-logo" />
        <span class="brand-copy">
          <span class="brand-lockup">
            <strong class="brand-cn">栖墨</strong>
            <span class="brand-en">INKREST</span>
          </span>
          <small>智能长篇写作空间</small>
        </span>
      </button>

      <div v-if="isInProject" class="project-badge">
        {{ projectStore.currentProject?.name }}
      </div>

      <nav class="nav-list" aria-label="主导航">
        <button
          v-for="item in menuItems.filter(i => i.path !== '/config')"
          :key="item.path"
          class="nav-item"
          :class="{ active: activePath === item.path }"
          @click="router.push(item.path)"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </button>
        <p v-if="!isInProject" class="nav-hint">点击栖墨 logo，开始你的创作之旅吧。</p>
      </nav>

      <div class="sidebar-bottom">
        <el-popover placement="right-end" trigger="click" width="340" @show="loadEngineStatus">
          <template #reference>
            <button
              class="engine-pill"
              :class="{ checking: engineChecking, ready: engineReady && !engineChecking, warn: engineWarn && !engineChecking }"
            >
              <span class="engine-dot" />
              <div>
                <strong>运行状态</strong>
                <small>{{ engineLabel }}</small>
              </div>
            </button>
          </template>
          <div class="engine-popover">
            <div class="engine-pop-head">
              <strong>创作环境检查</strong>
              <el-button text size="small" @click="loadEngineStatus">刷新</el-button>
            </div>
            <p class="engine-pop-hint">
              系统自检与创作环境（API、单进程、令牌、模型、开书清单、插件等）；向量部署见 设置 → 模型库 → 向量嵌入。
            </p>
            <div class="engine-stage-list">
              <div
                v-for="stage in engineStages"
                :key="stage.label"
                class="engine-stage"
                :class="{ 'clickable': getStageRoute(stage) }"
                @click="goToStage(stage)"
              >
                <span class="stage-dot" :class="{ ok: stage.ok, warn: stage.warn && !stage.ok }" />
                <div>
                  <strong>{{ stage.label }}</strong>
                  <small>{{ stage.detail }}</small>
                </div>
                <el-icon v-if="getStageRoute(stage)" class="stage-arrow"><ArrowRight /></el-icon>
              </div>
            </div>
          </div>
        </el-popover>

        <button
          class="nav-item"
          :class="{ active: activePath === '/trope-workshop' }"
          @click="router.push('/trope-workshop')"
        >
          <el-icon><MagicStick /></el-icon>
          <span>灵感工坊</span>
        </button>

        <button
          class="nav-item"
          :class="{ active: activePath === '/plugins' }"
          @click="router.push('/plugins')"
        >
          <el-icon><Cpu /></el-icon>
          <span>插件</span>
        </button>

        <button
          class="nav-item settings-btn"
          :class="{ active: activePath === '/config' }"
          @click="router.push('/config')"
        >
          <el-icon><Setting /></el-icon>
          <span>设置</span>
        </button>
      </div>
    </aside>

    <main class="workspace" :class="{ 'no-padding': route.path === '/writer' || route.path === '/reader' }">
      <router-view />
    </main>

    <SetupWizard
      :visible="showSetupWizard"
      @close="showSetupWizard = false"
      @completed="handleWizardCompleted"
    />

    <FirstBookGuide
      v-if="isInProject && projectStore.currentProject?.id"
      :project-id="projectStore.currentProject.id"
    />

    <NovelBatchRunDialog />
  </div>
</template>

<style>
html {
  font-size: 15px;
  color: var(--color-text);
  font-family: var(--font-sans);
  -webkit-font-smoothing: antialiased;
}

* { box-sizing: border-box; }
body {
  margin: 0;
  min-width: 1100px;
  background: var(--color-bg-app);
  font-size: 15px;
}
button, input, textarea, select { font-family: inherit; }
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-thumb {
  background: var(--color-text-subtle);
  border-radius: 999px;
}

.backend-offline-alert {
  position: fixed;
  top: 12px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 3000;
  width: min(560px, calc(100vw - 24px));
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
}

.app-shell {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  min-height: 100vh;
}

.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 22px 18px;
  background: var(--color-bg-sidebar);
  color: var(--color-text-sidebar);
}

.brand {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 11px;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.brand-logo {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  box-shadow: var(--shadow-brand);
}

.brand-lockup {
  display: flex;
  align-items: baseline;
  gap: 7px;
  white-space: nowrap;
}

.brand-cn {
  display: block;
  color: var(--color-brand-ink);
  font-family: "Microsoft YaHei UI", "Microsoft YaHei", sans-serif;
  font-size: 19px;
  font-weight: 800;
  letter-spacing: 2px;
  line-height: 1;
}

.brand-en {
  color: var(--color-brand-gold);
  font-family: Georgia, "Times New Roman", serif;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1.5px;
  line-height: 1;
}

.brand small {
  display: block;
  margin-top: 6px;
  color: var(--color-text-sidebar-dim);
  font-size: 11px;
  letter-spacing: 0.5px;
  white-space: nowrap;
}

.project-badge {
  overflow: hidden;
  padding: 10px 12px;
  border: 1px solid var(--color-primary-muted);
  border-radius: var(--radius-md);
  background: var(--color-primary-muted);
  color: var(--color-brand-ink);
  font-size: 14px;
  font-weight: 700;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: center;
}

.nav-list { display: grid; gap: 5px; }

.nav-hint {
  margin: 8px 4px 0;
  padding: 10px 10px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
  color: var(--color-text-sidebar-dim);
  font-size: 12px;
  line-height: 1.45;
}

.nav-item {
  width: 100%;
  height: 44px;
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 0 14px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  color: var(--color-text-sidebar-muted);
  cursor: pointer;
  font-size: 15px;
  font-weight: 600;
  text-align: left;
}

.nav-item:hover,
.nav-item.active {
  background: rgba(255, 255, 255, 0.06);
  color: var(--color-bg-surface);
}

.nav-item.active {
  border-color: rgba(198, 111, 79, 0.35);
  box-shadow: inset 3px 0 0 var(--color-primary);
}

.sidebar-bottom {
  margin-top: auto;
  display: grid;
  gap: 6px;
}

.engine-pill {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
  color: inherit;
  cursor: pointer;
  text-align: left;
}

.engine-pill:hover {
  border-color: rgba(198, 111, 79, 0.45);
  background: rgba(255, 255, 255, 0.07);
}

.engine-dot,
.stage-dot {
  width: 9px;
  height: 9px;
  flex: none;
  border-radius: 999px;
  background: var(--color-danger);
  box-shadow: 0 0 0 3px var(--color-danger-soft);
}

.engine-pill.checking .engine-dot {
  background: var(--color-text-sidebar-muted);
  box-shadow: 0 0 0 3px rgba(167, 179, 196, 0.22);
  animation: engine-pulse 1.2s ease-in-out infinite;
}

@keyframes engine-pulse {
  0%,
  100% {
    opacity: 0.55;
  }
  50% {
    opacity: 1;
  }
}

.engine-pill.ready .engine-dot,
.stage-dot.ok {
  background: var(--color-success);
  box-shadow: 0 0 0 3px var(--color-success-soft);
}

.engine-pill.ready.warn .engine-dot {
  background: var(--color-warning);
  box-shadow: 0 0 0 3px var(--color-warning-soft);
}

.engine-pill strong {
  display: block;
  color: var(--color-text-sidebar);
  font-size: 12px;
}

.engine-pill small {
  display: block;
  max-width: 170px;
  overflow: hidden;
  color: var(--color-text-sidebar-dim);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.engine-popover {
  display: grid;
  gap: 10px;
}

.engine-pop-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.engine-pop-hint {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--color-text-muted);
}

.stage-dot.warn {
  background: var(--color-warning);
  box-shadow: 0 0 0 3px var(--color-warning-soft);
}

.engine-stage-list {
  display: grid;
  gap: 8px;
  max-height: 440px;
  overflow-y: auto;
  overflow-x: hidden;
}

.engine-stage {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 8px 0;
  border-top: 1px solid var(--color-border-subtle);
}

.engine-stage:first-child { border-top: 0; }
.engine-stage strong {
  display: block;
  color: var(--color-text-strong);
  font-size: 13px;
}
.engine-stage small {
  display: block;
  margin-top: 2px;
  color: var(--color-text-muted);
  font-size: 12px;
}

.settings-btn {
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  padding-top: 6px;
}

.workspace {
  min-width: 0;
  padding: 30px 42px 42px;
  overflow: auto;
}

.workspace.no-padding {
  padding: 0;
  overflow: hidden;
  height: 100vh;
}

.fold-card {
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-surface);
  box-shadow: var(--shadow-card);
}

.fold-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 15px 18px;
  cursor: pointer;
  user-select: none;
}

.fold-head:hover {
  background: var(--color-bg-surface-muted);
}

.head-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.collapse-arrow {
  color: var(--color-text-subtle);
  font-size: 12px;
  transition: transform 0.18s ease;
}

.collapse-arrow.open {
  transform: rotate(90deg);
}

.fold-head h2 {
  margin: 0;
  color: var(--color-text-strong);
  font-size: 17px;
  font-weight: 800;
  letter-spacing: 0;
}

.fold-head p {
  margin: 4px 0 0;
  color: var(--color-text-muted);
  font-size: 13px;
}

.fold-body {
  display: grid;
  gap: 14px;
  padding: 0 18px 18px;
  border-top: 1px solid var(--color-border-subtle);
}

.fold-action {
  color: var(--color-bg-surface) !important;
  background: var(--color-primary) !important;
  border-color: var(--color-primary) !important;
  flex: none;
}

.fold-action:hover {
  background: var(--color-primary-hover) !important;
  border-color: var(--color-primary-hover) !important;
}

.panel {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-surface);
  box-shadow: var(--shadow-panel);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--color-border-subtle);
}

.panel-title {
  margin: 0;
  color: var(--color-text-strong);
  font-size: 17px;
  font-weight: 750;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.metric {
  min-height: 102px;
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-surface);
  box-shadow: var(--shadow-card);
}

.metric-label { color: var(--color-text-muted); font-size: 14px; }
.metric-value {
  margin-top: 8px;
  color: var(--color-primary);
  font-size: 30px;
  font-weight: 800;
}

@media (max-width: 1200px) {
  .metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

.engine-stage.clickable {
  cursor: pointer;
  transition: all 0.2s ease;
  padding: 8px;
  margin: 0 -8px;
  border-radius: 6px;
}
.engine-stage.clickable:hover {
  background: var(--color-bg-hover);
}
.stage-arrow {
  margin-left: auto;
  color: var(--color-text-subtle);
  font-size: 12px;
}
</style>
