import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import QuickCreateForm from '../components/QuickCreateForm.vue'
import { useProjectStore } from '../stores/project'
import { getConfig, listModels, analyzeNovelIntro } from '../api'
import { buildMinimalOutline, resolvePostCreateRoute } from '../utils/createOutline'
import { markPendingFirstBookGuide } from '../utils/firstBookGuide'
import { postCreateChecklistLines } from '../utils/projectReadiness'

import type { Composition } from '../types/preset'

export type CreateMode = 'quick' | 'ai' | 'parse'

const formatModelLabel = (model: any) => {
  if (!model) return ''
  return `${model.name || model.id}${model.model ? ` (${model.model})` : ''}`
}

const resolveAiGuideModel = (config: any, models: any[]) => {
  const llm = config?.llm || {}
  const safeModels = Array.isArray(models) ? models : []
  const modelsById = new Map(
    safeModels.filter((model: any) => model && model.id).map((model: any) => [model.id, model]),
  )
  const novelChat = llm.overrides?.novel_chat

  if (novelChat?.model_ref) return formatModelLabel(modelsById.get(novelChat.model_ref)) || novelChat.model_ref
  const dailyModelId = llm.daily_model_id || llm.default_model_id
  if (dailyModelId) return formatModelLabel(modelsById.get(dailyModelId)) || ''
  if (llm.provider && llm.provider !== 'static') return llm.model || llm.provider
  return ''
}

export function useCreateWizard() {
  const router = useRouter()
  const route = useRoute()
  const projectStore = useProjectStore()

  const activeMode = ref<CreateMode>('quick')
  const quickFormRef = ref<InstanceType<typeof QuickCreateForm> | null>(null)
  const creating = ref(false)
  const aiModelReady = ref(false)
  const aiModelLabel = ref('')

  const parseText = ref('')
  const fileName = ref('')
  const parseFileInput = ref<HTMLInputElement | null>(null)
  const analyzing = ref(false)

  const goBack = () => router.push('/')

  const finishCreateAndNavigate = async (scale: string, projectName: string, hasOutline = true) => {
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
    const hasOutline = Boolean(outline && (outline.macro_outline as unknown[])?.length)
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
      const composition = ctx.preset_composition as
        | { channel: string; theme: string; mechanisms: string[]; cool_points: string[] }
        | undefined

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

  const goToConfig = () => router.push('/config')

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

  return {
    activeMode,
    quickFormRef,
    creating,
    aiModelReady,
    aiModelLabel,
    parseText,
    fileName,
    parseFileInput,
    analyzing,
    goBack,
    goToConfig,
    handleAiComplete,
    handleQuickCreate,
    triggerQuickSubmit,
    triggerFileSelect,
    handleParseFileUpload,
    handleAnalyzeSubmit,
  }
}