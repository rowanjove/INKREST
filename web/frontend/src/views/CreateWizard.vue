<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Cpu, Lightning, MagicStick, Setting, Document, Upload } from '@element-plus/icons-vue'
import AiChatGuide from '../components/AiChatGuide.vue'
import QuickCreateForm from '../components/QuickCreateForm.vue'
import { useProjectStore } from '../stores/project'
import { getConfig, listModels, analyzeNovelIntro } from '../api'
import { buildMinimalOutline, resolvePostCreateRoute } from '../utils/createOutline'
import { markPendingFirstBookGuide } from '../utils/firstBookGuide'
import { postCreateChecklistLines } from '../utils/projectReadiness'

import type { Composition } from '../types/preset'

const router = useRouter()
const route = useRoute()
const projectStore = useProjectStore()
const activeMode = ref<'quick' | 'ai' | 'parse'>('quick')
const quickFormRef = ref<InstanceType<typeof QuickCreateForm> | null>(null)
const creating = ref(false)
const aiModelReady = ref(false)
const aiModelLabel = ref('')

// Content Analysis state
const parseText = ref('')
const fileName = ref('')
const parseFileInput = ref<HTMLInputElement | null>(null)
const analyzing = ref(false)

const formatModelLabel = (model: any) => {
  if (!model) return ''
  return `${model.name || model.id}${model.model ? ` (${model.model})` : ''}`
}

const resolveAiGuideModel = (config: any, models: any[]) => {
  const llm = config?.llm || {}
  const safeModels = Array.isArray(models) ? models : []
  const modelsById = new Map(
    safeModels
      .filter((model: any) => model && model.id)
      .map((model: any) => [model.id, model])
  )
  const novelChat = llm.overrides?.novel_chat

  if (novelChat?.model_ref) return formatModelLabel(modelsById.get(novelChat.model_ref)) || novelChat.model_ref
  const dailyModelId = llm.daily_model_id || llm.default_model_id
  if (dailyModelId) return formatModelLabel(modelsById.get(dailyModelId)) || ''
  if (llm.provider && llm.provider !== 'static') return llm.model || llm.provider
  return ''
}

onMounted(async () => {
  try {
    const [{ data: models }, { data: config }] = await Promise.all([listModels(), getConfig()])
    aiModelLabel.value = resolveAiGuideModel(config, models)
    aiModelReady.value = Boolean(aiModelLabel.value)
  } catch {
    aiModelReady.value = false
  }

  const q = route.query
  if (q.mode === 'quick' || q.from === 'trope') {
    activeMode.value = 'quick'
    const composition: Composition | null =
      q.theme && q.channel
        ? {
            channel: String(q.channel),
            theme: String(q.theme),
            mechanisms: String(q.mechanisms || '')
              .split(',')
              .map((s) => s.trim())
              .filter(Boolean),
            cool_points: String(q.cool_points || '')
              .split(',')
              .map((s) => s.trim())
              .filter(Boolean),
          }
        : null
    quickFormRef.value?.applyInitial({
      name: String(q.name || ''),
      description: String(q.description || ''),
      genre: String(q.genre || q.theme || ''),
      scale: String(q.scale || 'medium'),
      target_chapters: q.target_chapters ? Number(q.target_chapters) : undefined,
      composition,
    })
  }
  if (q.mode === 'ai') activeMode.value = 'ai'
  if (q.mode === 'parse') activeMode.value = 'parse'
})

const goBack = () => router.push('/')

const finishCreateAndNavigate = async (
  scale: string,
  projectName: string,
  hasOutline = true,
) => {
  const { path, preferOutline } = resolvePostCreateRoute(scale, hasOutline)
  const steps = postCreateChecklistLines(preferOutline).join('\n')

  try {
    await ElMessageBox.confirm(
      `「${projectName}」已创建。\n\n建议下一步：\n${steps}`,
      '创建成功',
      {
        confirmButtonText: preferOutline ? '去大纲页' : '进工作台',
        cancelButtonText: '稍后再说',
        distinguishCancelAndClose: true,
        type: 'success',
      },
    )
    router.push({ path, query: { welcome: '1' } })
  } catch {
    router.push({ path, query: { welcome: '1' } })
  }
}

const createProject = async (
  name: string,
  description: string,
  extra: Record<string, unknown>,
  presetId?: string,
) => {
  const project = await projectStore.createProject(name, description, presetId, extra)
  await projectStore.switchProject(project.id)
  markPendingFirstBookGuide(project.id)
  ElMessage.success('作品已创建')
  const scale = String(extra.scale || '')
  const outline = extra.outline as Record<string, unknown> | undefined
  const hasOutline = Boolean(
    outline && (outline.macro_outline as unknown[])?.length,
  )
  await finishCreateAndNavigate(scale, name, hasOutline)
}

const handleAiComplete = async (data: {
  name: string
  description: string
  genre: string
  context: Record<string, unknown>
}) => {
  creating.value = true
  try {
    const ctx = (data.context as Record<string, any>) || {}
    const card = (ctx.summary_card as Record<string, any>) || {}
    const readerPromise = (ctx.reader_promise as Record<string, any>) || {}
    const conflictStage = (ctx.conflict_stage as Record<string, any>) || {}
    const scaleTarget = (ctx.target_chars as number[]) || [2000, 3000]
    const targetChapters = (ctx.target_chapters as number) || 200
    const scale = (ctx.scale as string) || ''
    const scaleLabel = (ctx.scale_label as string) || ''
    const presetId = (ctx.preset_id as string) || undefined
    const composition = ctx.preset_composition as { channel: string; theme: string; mechanisms: string[]; cool_points: string[] } | undefined

    const outline: Record<string, unknown> = {
      title_options: card.title_suggestions || [data.name],
      logline: card.logline || data.description,
      core_theme: ctx.theme || '',
      genre_positioning: data.genre || card.genre_positioning || '',
      target_reader: card.target_reader || '',
      reader_promise: card.reader_promise || [],
      tone: card.tone || '',
      protagonist: ctx.protagonist || {},
      reader_expectation: readerPromise,
      conflict_stage: conflictStage,
      serial_engine: ctx.serial_engine || {},
      character_network: ctx.character_network || {},
      growth_arcs: ctx.growth_arcs || {},
      volume_skeleton: ctx.volume_skeleton || {},
      turning_points: ctx.turning_points || {},
      antagonistic_forces: conflictStage.external_opposition || [],
      world_rules: conflictStage.world_rules || [],
      conflict: conflictStage.conflict || '',
    }
    if (scale || scaleLabel) {
      outline.scale_profile = {
        scale,
        label: scaleLabel,
        target_chapters: targetChapters,
      }
    }

    const extra: Record<string, unknown> = {
      genre: data.genre,
      target_chapters: targetChapters,
      scale,
      scale_label: scaleLabel,
      target_chars_per_chapter: scaleTarget,
      outline,
    }
    if (composition) {
      extra.preset_channel = composition.channel
      extra.preset_theme = composition.theme
      extra.preset_mechanisms = composition.mechanisms
      extra.preset_cool_points = composition.cool_points
    }
    await createProject(data.name, data.description, extra, presetId)
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || err.message || '创建失败')
  } finally {
    creating.value = false
  }
}

const handleQuickCreate = async (data: {
  name: string
  description: string
  genre: string
  channel: string
  target_chapters: number
  scale: string
  scale_label: string
  target_chars_per_chapter: number[]
  composition: {
    channel: string
    theme: string
    mechanisms: string[]
    cool_points: string[]
  } | null
}) => {
  creating.value = true
  try {
    const outline = buildMinimalOutline(data)
    const extra: Record<string, unknown> = {
      genre: data.genre,
      channel: data.channel,
      target_chapters: data.target_chapters,
      scale: data.scale,
      scale_label: data.scale_label,
      target_chars_per_chapter: data.target_chars_per_chapter,
      outline,
    }
    if (data.composition) {
      extra.preset_channel = data.composition.channel
      extra.preset_theme = data.composition.theme
      extra.preset_mechanisms = data.composition.mechanisms
      extra.preset_cool_points = data.composition.cool_points
    }
    await createProject(data.name, data.description, extra)
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || err.message || '创建失败')
  } finally {
    creating.value = false
  }
}

const triggerQuickSubmit = () => {
  quickFormRef.value?.handleSubmit()
}

// Content Analysis triggers
const triggerFileSelect = () => {
  parseFileInput.value?.click()
}

const handleParseFileUpload = (event: Event) => {
  const target = event.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  fileName.value = file.name
  const reader = new FileReader()
  reader.onload = (e) => {
    const text = e.target?.result as string
    parseText.value = text || ''
    ElMessage.success(`成功导入「${file.name}」共 ${parseText.value.length} 字`)
  }
  reader.readAsText(file, 'utf-8')
}

const handleAnalyzeSubmit = async () => {
  if (!parseText.value.trim()) {
    ElMessage.warning('请先粘贴文字或上传文件！')
    return
  }

  analyzing.value = true
  try {
    ElMessage.info('大模型正在分析您的设定中，请稍候...')
    const { data } = await analyzeNovelIntro(parseText.value)
    await handleAiComplete(data)
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail || err.message || '分析并创建失败')
  } finally {
    analyzing.value = false
  }
}
</script>

<template>
  <section class="create-page">
    <header class="create-header">
      <el-button text @click="goBack" class="back-btn">
        <el-icon><ArrowLeft /></el-icon>
        返回书库
      </el-button>
      <h1>新建作品</h1>
      <p>默认从快速创建开始；支持由 AI 进行对话引导或根据文字大纲内容解析建档。</p>
    </header>

    <div class="mode-tabs">
      <button class="mode-tab" :class="{ active: activeMode === 'quick' }" @click="activeMode = 'quick'">
        <el-icon :size="20"><Lightning /></el-icon>
        <div>
          <strong>快速创建</strong>
          <small>填写表单，直接开始</small>
        </div>
        <el-tag size="small" type="warning" effect="dark" class="rec-tag">默认</el-tag>
      </button>
      <button class="mode-tab" :class="{ active: activeMode === 'parse' }" @click="activeMode = 'parse'">
        <el-icon :size="20"><Document /></el-icon>
        <div>
          <strong>内容分析导入</strong>
          <small>粘贴文字/上传草稿解析建档</small>
        </div>
      </button>
      <button class="mode-tab" :class="{ active: activeMode === 'ai' }" @click="activeMode = 'ai'">
        <el-icon :size="20"><MagicStick /></el-icon>
        <div>
          <strong>AI 创作引导</strong>
          <small>和 AI 聊几步自动构建雏形</small>
        </div>
      </button>
    </div>

    <div v-if="activeMode === 'ai'" class="engine-mini" :class="{ ready: aiModelReady }">
      <el-icon><Cpu /></el-icon>
      <span>{{ aiModelReady ? `AI 引导模型：${aiModelLabel}` : 'AI 引导模型未就绪' }}</span>
      <el-button text size="small" @click="router.push('/config')">模型设置</el-button>
    </div>

    <div class="mode-content">
      <div v-if="activeMode === 'ai' && !aiModelReady" class="no-model-warning">
        <h3>尚未配置 LLM 模型</h3>
        <p>AI 创作引导需要至少一个可用模型。你仍然可以使用快速创建或内容分析导入。</p>
        <div class="warning-actions">
          <el-button @click="activeMode = 'quick'">切换到快速创建</el-button>
          <el-button type="primary" :icon="Setting" @click="router.push('/config')">去设置</el-button>
        </div>
      </div>
      <AiChatGuide v-else-if="activeMode === 'ai'" :model-label="aiModelLabel" @complete="handleAiComplete" />
      
      <div v-else-if="activeMode === 'parse'" class="quick-wrapper">
        <div class="parse-container">
          <div class="parse-intro">
            <h3>粘贴文字或上传文件，让 AI 智能解析小说设定并一键建档</h3>
            <p>粘贴脑洞、大纲或素材，或上传 .md / .txt（Word 请先另存为 txt）。大模型将分析题材、拟定书名与主角，并生成世界观与读者承诺草案。</p>
          </div>
          
          <el-input
            v-model="parseText"
            type="textarea"
            :rows="12"
            placeholder="请在此粘贴您的小说脑洞、大纲、构想、角色卡或背景描述（越详尽分析越精准）..."
            class="parse-textarea"
          />
          
          <div class="parse-upload-row">
            <el-button
              type="warning"
              plain
              size="small"
              :icon="Upload"
              @click="triggerFileSelect"
            >
              上传 Markdown/Txt 文件
            </el-button>
            <input
              type="file"
              ref="parseFileInput"
              accept=".md,.txt,.text"
              style="display: none"
              @change="handleParseFileUpload"
            />
            <span v-if="fileName" class="uploaded-filename">已选择文件: <strong>{{ fileName }}</strong> (共 {{ parseText.length }} 字)</span>
          </div>
        </div>
        <div class="quick-footer">
          <el-button @click="goBack">取消</el-button>
          <el-button
            type="primary"
            :loading="analyzing"
            :disabled="!parseText.trim()"
            @click="handleAnalyzeSubmit"
          >
            开始分析并创建小说
          </el-button>
        </div>
      </div>

      <div v-else class="quick-wrapper">
        <QuickCreateForm ref="quickFormRef" @create="handleQuickCreate" />
        <div class="quick-footer">
          <el-button @click="goBack">取消</el-button>
          <el-button type="primary" :loading="creating" @click="triggerQuickSubmit">创建并进入</el-button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.create-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 32px 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.create-header {
  display: grid;
  gap: 4px;
}

.back-btn {
  justify-self: start;
  margin-bottom: 8px;
  color: #6b7280;
}

.create-header h1 {
  margin: 0;
  color: #111827;
  font-size: 28px;
  font-weight: 760;
}

.create-header p {
  margin: 0;
  color: #6b7280;
  font-size: 15px;
}

.mode-tabs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.mode-tab {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 76px;
  padding: 16px 20px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  background: var(--color-bg-surface);
  color: #374151;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s;
}

.mode-tab:hover,
.mode-tab.active {
  border-color: #c66f4f;
  box-shadow: 0 4px 16px rgba(198, 111, 79, 0.12);
}

.mode-tab .el-icon {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: #f3f4f6;
  color: #6b7280;
}

.mode-tab.active .el-icon {
  background: #c66f4f;
  color: var(--color-bg-surface);
}

.mode-tab div {
  display: grid;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.mode-tab strong {
  font-size: 14px;
}

.mode-tab small {
  color: #9ca3af;
  font-size: 11px;
}

.engine-mini {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid #f3d1c4;
  border-radius: 8px;
  background: #fff7f3;
  color: #9a3412;
  font-size: 13px;
}

.engine-mini.ready {
  border-color: #bbf7d0;
  background: #f0fdf4;
  color: #166534;
}

.mode-content {
  min-width: 0;
}

.quick-wrapper,
.no-model-warning {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: var(--color-bg-surface);
  padding: 24px;
}

.quick-footer,
.warning-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #eef2f7;
}

.no-model-warning h3 {
  margin: 0 0 8px;
  color: #111827;
}

.no-model-warning p {
  margin: 0;
  color: #6b7280;
}

.parse-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.parse-intro h3 {
  margin: 0 0 6px 0;
  font-size: 16px;
  color: #111827;
}

.parse-intro p {
  margin: 0;
  font-size: 13.5px;
  color: #6b7280;
  line-height: 1.5;
}

.parse-textarea {
  font-family: inherit;
}

.parse-upload-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 4px;
}

.uploaded-filename {
  font-size: 13px;
  color: #374151;
}

.rec-tag {
  margin-left: auto;
}
</style>
