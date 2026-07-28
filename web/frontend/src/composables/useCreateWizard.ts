import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import QuickCreateForm from '../components/QuickCreateForm.vue'
import { useProjectStore } from '../stores/project'
import { analyzeNovelIntro, getConfig, listModels } from '../api'
import { buildMinimalOutline } from '../utils/createOutline'
import { markPendingFirstBookGuide } from '../utils/firstBookGuide'
import type { Composition } from '../types/preset'

export type CreateMode = 'quick' | 'ai' | 'parse'

export type QuickCreateDraft = {
  name: string
  description: string
  genre: string
  channel: string
  target_chapters: number
  scale: string
  scale_label: string
  target_chars_per_chapter: number[]
  composition: Composition | null
}

export type AiCreateDraft = {
  name: string
  description: string
  genre: string
  context: Record<string, unknown>
}

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
  if (novelChat?.model_ref) {
    return formatModelLabel(modelsById.get(novelChat.model_ref)) || novelChat.model_ref
  }
  const dailyModelId = llm.daily_model_id || llm.default_model_id
  if (dailyModelId) return formatModelLabel(modelsById.get(dailyModelId)) || ''
  if (llm.provider && llm.provider !== 'static') return llm.model || llm.provider
  return ''
}

export function useCreateWizard() {
  const router = useRouter()
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
  const pendingQuick = ref<QuickCreateDraft | null>(null)
  const pendingAi = ref<AiCreateDraft | null>(null)

  const hasDraft = computed(() => Boolean(pendingQuick.value || pendingAi.value))
  const draftSummary = computed(() => {
    const draft = pendingQuick.value || pendingAi.value
    if (!draft) return null
    const context = pendingAi.value?.context as Record<string, any> | undefined
    return {
      name: draft.name,
      genre: draft.genre || '未指定题材',
      scale: pendingQuick.value?.scale_label || context?.scale_label || '在策划中心继续确认',
      targetChapters: pendingQuick.value?.target_chapters || context?.target_chapters || 0,
    }
  })

  const createProject = async (
    name: string,
    description: string,
    extra: Record<string, unknown>,
    presetId?: string,
  ) => {
    const project = await projectStore.createProject(name, description, presetId, extra)
    await projectStore.switchProject(project.id)
    markPendingFirstBookGuide(project.id)
    ElMessage.success('作品骨架已创建')
    await router.push({ path: '/outline', query: { welcome: '1' } })
  }

  const handleAiComplete = (data: AiCreateDraft) => {
    pendingQuick.value = null
    pendingAi.value = data
  }

  const commitAiCreate = async (data: AiCreateDraft) => {
    const ctx = (data.context as Record<string, any>) || {}
    const card = (ctx.summary_card as Record<string, any>) || {}
    const readerPromise = (ctx.reader_promise as Record<string, any>) || {}
    const conflictStage = (ctx.conflict_stage as Record<string, any>) || {}
    const targetChapters = (ctx.target_chapters as number) || 200
    const scale = (ctx.scale as string) || ''
    const scaleLabel = (ctx.scale_label as string) || ''
    const composition = ctx.preset_composition as Composition | undefined
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
      outline.scale_profile = { scale, label: scaleLabel, target_chapters: targetChapters }
    }
    const extra: Record<string, unknown> = {
      genre: data.genre,
      target_chapters: targetChapters,
      scale,
      scale_label: scaleLabel,
      target_chars_per_chapter: (ctx.target_chars as number[]) || [2000, 3000],
      outline,
    }
    if (composition) {
      extra.preset_channel = composition.channel
      extra.preset_theme = composition.theme
      extra.preset_mechanisms = composition.mechanisms
      extra.preset_cool_points = composition.cool_points
    }
    await createProject(data.name, data.description, extra, ctx.preset_id)
  }

  const handleQuickCreate = (data: QuickCreateDraft) => {
    pendingAi.value = null
    pendingQuick.value = data
  }

  const commitQuickCreate = async (data: QuickCreateDraft) => {
    const extra: Record<string, unknown> = {
      genre: data.genre,
      channel: data.channel,
      target_chapters: data.target_chapters,
      scale: data.scale,
      scale_label: data.scale_label,
      target_chars_per_chapter: data.target_chars_per_chapter,
      outline: buildMinimalOutline(data),
    }
    if (data.composition) {
      extra.preset_channel = data.composition.channel
      extra.preset_theme = data.composition.theme
      extra.preset_mechanisms = data.composition.mechanisms
      extra.preset_cool_points = data.composition.cool_points
    }
    await createProject(data.name, data.description, extra)
  }

  const commitCreate = async () => {
    if (!hasDraft.value || creating.value) return
    creating.value = true
    try {
      if (pendingQuick.value) await commitQuickCreate(pendingQuick.value)
      else if (pendingAi.value) await commitAiCreate(pendingAi.value)
    } catch (err: any) {
      ElMessage.error(err?.response?.data?.detail || err.message || '创建失败')
    } finally {
      creating.value = false
    }
  }

  const clearDraft = () => {
    pendingQuick.value = null
    pendingAi.value = null
  }

  const triggerQuickSubmit = () => quickFormRef.value?.handleSubmit()
  const triggerFileSelect = () => parseFileInput.value?.click()

  const handleParseFileUpload = (event: Event) => {
    const target = event.target as HTMLInputElement
    const file = target.files?.[0]
    if (!file) return
    fileName.value = file.name
    const reader = new FileReader()
    reader.onload = (e) => {
      parseText.value = String(e.target?.result || '')
      ElMessage.success(`成功导入「${file.name}」共 ${parseText.value.length} 字`)
    }
    reader.readAsText(file, 'utf-8')
  }

  const handleAnalyzeSubmit = async () => {
    if (!parseText.value.trim()) {
      ElMessage.warning('请先粘贴文字或上传文件')
      return
    }
    analyzing.value = true
    try {
      ElMessage.info('正在分析设定，请稍候…')
      const { data } = await analyzeNovelIntro(parseText.value)
      handleAiComplete(data)
    } catch (err: any) {
      ElMessage.error(err?.response?.data?.detail || err.message || '分析失败')
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
  }
}
