<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Document, Lightning, MagicStick, Reading } from '@element-plus/icons-vue'
import CreateQuickPane from '../components/create/CreateQuickPane.vue'
import CreateParsePane from '../components/create/CreateParsePane.vue'
import CreateAiPane from '../components/create/CreateAiPane.vue'
import PageShell from '../shared/ui/PageShell.vue'
import { useCreateWizard } from '../composables/useCreateWizard'
import {
  CREATE_STEPS,
  canEnterDetails,
  sourceMode,
  type CreationApproach,
  type CreationSource,
} from '../features/create/createFlow'

const route = useRoute()
const router = useRouter()
const step = ref(0)
const approach = ref<CreationApproach>('professional')
const source = ref<CreationSource>(
  route.query.source === 'template' || route.query.from === 'trope'
    ? 'template'
    : route.query.mode === 'ai'
      ? 'ai'
      : route.query.mode === 'parse'
        ? 'parse'
        : 'quick',
)

const {
  activeMode,
  quickFormRef,
  creating,
  aiModelReady,
  aiModelLabel,
  parseText,
  fileName,
  parseFileInput,
  analyzing,
  hasDraft,
  draftSummary,
  goToConfig,
  handleAiComplete,
  handleQuickCreate,
  triggerQuickSubmit,
  triggerFileSelect,
  handleParseFileUpload,
  handleAnalyzeSubmit,
  commitCreate,
  clearDraft,
} = useCreateWizard()

const sourceOptions = [
  { id: 'quick', title: '快速输入', description: '从书名、题材和一句话创意开始。', icon: Lightning },
  { id: 'ai', title: 'AI 引导', description: '通过对话逐步澄清卖点和人物。', icon: MagicStick },
  { id: 'parse', title: '大纲导入', description: '解析已有脑洞、设定或章节草稿。', icon: Document },
  { id: 'template', title: '套路模板', description: '从频道、主题、机制和爽点组合开始。', icon: Reading },
] as const

const modelBlocked = computed(() => !canEnterDetails(source.value, aiModelReady.value))

watch(source, (value) => {
  activeMode.value = sourceMode(value)
  clearDraft()
}, { immediate: true })

watch(hasDraft, (ready) => {
  if (ready) step.value = 3
})

function next() {
  if (step.value === 1 && modelBlocked.value) return
  if (step.value < 2) step.value += 1
}

function back() {
  if (step.value === 0) {
    router.push('/')
    return
  }
  if (step.value === 3) clearDraft()
  step.value -= 1
}
</script>

<template>
  <PageShell
    title="新建作品"
    description="把建书需要的选择集中在一个流程里；只有 AI 相关来源缺少模型时才会阻塞。"
    eyebrow="创作起点"
    compact
  >
    <template #actions>
      <el-button text :icon="ArrowLeft" @click="back">返回</el-button>
    </template>

    <el-steps :active="step" finish-status="success" align-center class="create-steps">
      <el-step v-for="label in CREATE_STEPS" :key="label" :title="label" />
    </el-steps>

    <section v-if="step === 0" class="choice-grid">
      <button
        type="button"
        class="choice-card"
        :class="{ active: approach === 'auto' }"
        @click="approach = 'auto'"
      >
        <strong>自动化生产</strong>
        <span>先建立可运行骨架，后续由生产控制台按确认步骤推进。</span>
      </button>
      <button
        type="button"
        class="choice-card"
        :class="{ active: approach === 'professional' }"
        @click="approach = 'professional'"
      >
        <strong>专业写作</strong>
        <span>先在策划中心完善人物、世界和结构，再进入正文生产。</span>
      </button>
    </section>

    <section v-else-if="step === 1">
      <div class="source-grid">
        <button
          v-for="item in sourceOptions"
          :key="item.id"
          type="button"
          class="source-card"
          :class="{ active: source === item.id }"
          @click="source = item.id"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <strong>{{ item.title }}</strong>
          <span>{{ item.description }}</span>
        </button>
      </div>
      <div v-if="modelBlocked" class="readiness-blocker" role="alert">
        <div>
          <strong>当前来源需要可用的 AI 模型</strong>
          <p>配置一个日常模型后即可继续；快速输入和套路模板不受影响。</p>
        </div>
        <el-button type="primary" plain @click="goToConfig">前往模型设置</el-button>
      </div>
    </section>

    <section v-else-if="step === 2" class="details-step">
      <p v-if="source === 'template'" class="source-note">
        在“预设模板”中组合频道、主题、机制和爽点。模板已合并到建书流程，不再需要独立工坊。
      </p>
      <CreateAiPane
        v-if="activeMode === 'ai'"
        :ai-model-ready="aiModelReady"
        :ai-model-label="aiModelLabel"
        @switch-to-quick="source = 'quick'"
        @go-to-config="goToConfig"
        @ai-complete="handleAiComplete"
      />
      <CreateParsePane
        v-else-if="activeMode === 'parse'"
        v-model:parse-text="parseText"
        v-model:parse-file-input="parseFileInput"
        :analyzing="analyzing"
        :file-name="fileName"
        @go-back="back"
        @trigger-file-select="triggerFileSelect"
        @handle-parse-file-upload="handleParseFileUpload"
        @handle-analyze-submit="handleAnalyzeSubmit"
      />
      <CreateQuickPane
        v-else
        v-model:quick-form-ref="quickFormRef"
        :creating="creating"
        @go-back="back"
        @quick-create="handleQuickCreate"
        @trigger-submit="triggerQuickSubmit"
      />
    </section>

    <section v-else class="confirm-card">
      <div>
        <p class="confirm-eyebrow">即将建立作品骨架</p>
        <h2>《{{ draftSummary?.name }}》</h2>
        <dl>
          <div><dt>工作方式</dt><dd>{{ approach === 'auto' ? '自动化生产' : '专业写作' }}</dd></div>
          <div><dt>素材来源</dt><dd>{{ sourceOptions.find((item) => item.id === source)?.title }}</dd></div>
          <div><dt>题材</dt><dd>{{ draftSummary?.genre }}</dd></div>
          <div><dt>规模</dt><dd>{{ draftSummary?.scale }}</dd></div>
          <div v-if="draftSummary?.targetChapters"><dt>目标章节</dt><dd>{{ draftSummary.targetChapters }} 章</dd></div>
        </dl>
        <p class="confirm-note">建档后进入策划中心继续补全实体和结构，不会自动触发章节生成。</p>
      </div>
      <el-button type="primary" size="large" :loading="creating" @click="commitCreate">
        确认建档并进入策划
      </el-button>
    </section>

    <footer v-if="step < 2" class="flow-actions">
      <el-button @click="back">{{ step === 0 ? '取消' : '上一步' }}</el-button>
      <el-button type="primary" :disabled="modelBlocked" @click="next">下一步</el-button>
    </footer>
  </PageShell>
</template>

<style scoped>
.create-steps { margin: var(--space-4) 0 var(--space-7); }

.choice-grid,
.source-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-4);
}

.choice-card,
.source-card {
  display: grid;
  align-content: start;
  gap: var(--space-2);
  min-height: 140px;
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-surface);
  color: var(--color-text);
  text-align: left;
  cursor: pointer;
}

.source-card { grid-template-columns: auto 1fr; min-height: 112px; }
.source-card .el-icon { grid-row: 1 / span 2; color: var(--color-primary); font-size: 24px; }
.choice-card.active,
.source-card.active { border-color: var(--color-primary); box-shadow: var(--shadow-focus); }
.choice-card strong,
.source-card strong { color: var(--color-text-strong); font-size: 16px; }
.choice-card span,
.source-card span { color: var(--color-text-muted); font-size: 13px; line-height: 1.6; }

.readiness-blocker,
.source-note {
  margin-top: var(--space-4);
  padding: var(--space-4);
  border: 1px solid color-mix(in srgb, var(--color-warning) 45%, var(--color-border));
  border-radius: var(--radius-md);
  background: color-mix(in srgb, var(--color-warning) 8%, var(--color-bg-surface));
}

.readiness-blocker { display: flex; justify-content: space-between; gap: var(--space-4); }
.readiness-blocker p,
.source-note { color: var(--color-text-muted); font-size: 13px; }
.readiness-blocker p { margin: 4px 0 0; }
.source-note { margin-bottom: var(--space-4); line-height: 1.6; }
.details-step { min-width: 0; }

.confirm-card {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: var(--space-6);
  padding: var(--space-6);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-surface);
}

.confirm-eyebrow { margin: 0; color: var(--color-primary); font-size: 12px; font-weight: 700; }
.confirm-card h2 { margin: 5px 0 var(--space-4); color: var(--color-text-strong); }
.confirm-card dl { display: grid; gap: 8px; margin: 0; }
.confirm-card dl div { display: grid; grid-template-columns: 88px 1fr; gap: 12px; }
.confirm-card dt { color: var(--color-text-muted); }
.confirm-card dd { margin: 0; color: var(--color-text-strong); }
.confirm-note { margin: var(--space-4) 0 0; color: var(--color-text-muted); font-size: 13px; }

.flow-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  margin-top: var(--space-5);
}

@media (max-width: 720px) {
  .choice-grid,
  .source-grid { grid-template-columns: 1fr; }
  .readiness-blocker,
  .confirm-card { align-items: stretch; flex-direction: column; }
}
</style>
