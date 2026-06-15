<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CircleCheck, MagicStick, Plus, Reading } from '@element-plus/icons-vue'
import SystemReadinessPanel from '../components/SystemReadinessPanel.vue'
import { apiErrorMessage, getOnboardingStatus, importDemoProject } from '../api'
import { useProjectStore } from '../stores/project'
import { completeOnboarding, markAppTourPending, shouldStartAppTour } from '../composables/useAppTour'

const router = useRouter()
const projectStore = useProjectStore()
const step = ref(0)
const loading = ref(false)
const status = ref({
  has_projects: false,
  llm_ready: false,
  demo_available: true,
  demo_id: 'demo-factory-novel',
})

const canFinish = computed(() => status.value.has_projects)

async function loadStatus() {
  try {
    const { data } = await getOnboardingStatus()
    status.value = {
      has_projects: !!data.has_projects,
      llm_ready: !!data.llm_ready,
      demo_available: data.demo_available !== false,
      demo_id: data.demo_id || 'demo-factory-novel',
    }
    if (data.has_projects) {
      step.value = 2
    }
  } catch {
    /* backend warming */
  }
}

function goConfig() {
  router.push('/config')
}

function goCreate() {
  completeOnboarding()
  router.push('/create')
}

async function importDemo() {
  loading.value = true
  try {
    const { data } = await importDemoProject(status.value.demo_id)
    await projectStore.fetchProjects()
    await projectStore.fetchCurrent()
    ElMessage.success(
      data.status === 'existing' ? '示例书已在书库中，已为你打开' : '示例书已导入，可开始体验工厂流程',
    )
    status.value.has_projects = true
    step.value = 2
  } catch (error: unknown) {
    ElMessage.error(apiErrorMessage(error, '示例书导入失败'))
  } finally {
    loading.value = false
  }
}

function finish() {
  completeOnboarding()
  if (shouldStartAppTour()) {
    markAppTourPending()
  }
  if (projectStore.currentProject?.id) {
    router.push('/workspace?focus=pipeline')
    return
  }
  router.push('/')
}

function skipToLibrary() {
  completeOnboarding()
  router.push('/')
}

onMounted(loadStatus)
</script>

<template>
  <section class="onboarding-page">
    <header class="onboarding-head">
      <h1>欢迎使用栖墨 INKREST</h1>
      <p>三步跑通环境检查、模型配置与首本小说——约 3 分钟进入 AI 工厂生产流程。</p>
      <button type="button" class="onboarding-skip" @click="skipToLibrary">跳过向导，直接去书库</button>
    </header>

    <el-steps :active="step" align-center finish-status="success" class="onboarding-steps">
      <el-step title="系统就绪" description="确认 API、单进程与插件安全" />
      <el-step title="模型配置" description="配通 1 个日常 LLM 即可开写" />
      <el-step title="开第一本书" description="推荐先导入示例书体验" />
    </el-steps>

    <div v-if="step === 0" class="onboarding-panel">
      <SystemReadinessPanel />
      <div class="panel-actions">
        <el-button type="primary" @click="step = 1">下一步：检查模型</el-button>
      </div>
    </div>

    <div v-else-if="step === 1" class="onboarding-panel">
      <div class="model-card" :class="{ ready: status.llm_ready }">
        <el-icon><CircleCheck v-if="status.llm_ready" /><Reading v-else /></el-icon>
        <div>
          <strong>{{ status.llm_ready ? '日常模型已就绪，可以开写' : '还差一步：配置日常模型' }}</strong>
          <p>打开设置页，填入 LLM 提供方与 API Key 并测试连通。向量嵌入可之后再配，不挡首本体验。</p>
        </div>
      </div>
      <div class="panel-actions">
        <el-button @click="step = 0">上一步</el-button>
        <el-button plain @click="goConfig">打开设置</el-button>
        <el-button type="primary" @click="step = 2">下一步：开第一本书</el-button>
      </div>
    </div>

    <div v-else class="onboarding-panel">
      <div class="start-grid">
        <article class="start-card featured">
          <h3>推荐：导入示例书</h3>
          <p>内置《星河试炼：工厂示例书》——含大纲、资产与 3 章正文，导入后直达工厂控制台与连写区。</p>
          <el-button
            type="primary"
            :icon="MagicStick"
            :loading="loading"
            :disabled="!status.demo_available"
            @click="importDemo"
          >
            导入示例书
          </el-button>
        </article>
        <article class="start-card">
          <h3>新建作品</h3>
          <p>从灵感、套路工坊或快速创建向导开书，适合已有题材方向的用户。</p>
          <el-button type="success" plain :icon="Plus" @click="goCreate">新建小说</el-button>
        </article>
      </div>
      <div class="panel-actions">
        <el-button @click="step = 1">上一步</el-button>
        <el-button type="primary" :disabled="!canFinish" @click="finish">进入工厂控制台</el-button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.onboarding-page {
  max-width: 920px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 8px 4px 32px;
}

.onboarding-head h1 {
  margin: 0 0 6px;
  font-size: 28px;
}

.onboarding-head p {
  margin: 0;
  color: var(--color-text-muted);
}

.onboarding-skip {
  margin-top: 8px;
  border: none;
  background: transparent;
  color: var(--color-primary);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
}

.onboarding-skip:hover {
  text-decoration: underline;
}

.onboarding-steps {
  margin: 8px 0 4px;
}

.onboarding-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  background: var(--color-bg-surface);
}

.model-card {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 14px;
  border-radius: 8px;
  border: 1px solid #fde2e2;
  background: #fff5f5;
}

.model-card.ready {
  border-color: #c6f6d5;
  background: #f0fff4;
}

.model-card strong {
  display: block;
  margin-bottom: 4px;
}

.model-card p {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-muted);
}

.start-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.start-card {
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-surface-muted);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.start-card.featured {
  border-color: rgba(0, 122, 255, 0.35);
  background: rgba(0, 122, 255, 0.04);
}

.start-card h3 {
  margin: 0;
  font-size: 16px;
}

.start-card p {
  margin: 0;
  flex: 1;
  font-size: 13px;
  color: var(--color-text-muted);
  line-height: 1.5;
}

.panel-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

@media (max-width: 760px) {
  .start-grid {
    grid-template-columns: 1fr;
  }
}
</style>
