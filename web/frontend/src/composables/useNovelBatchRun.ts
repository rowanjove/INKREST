import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { storeToRefs } from 'pinia'
import {
  continueNovel,
  ensureNovelQueue,
  getArcProgress,
  getChapterCount,
  getConfig,
  getEmbeddingStatus,
  getNovelBatchStatus,
  getOutline,
  listAssets,
  listModels,
} from '../api'
import { buildReadinessItems, readinessAllOk } from '../utils/projectReadiness'
import { useProjectStore } from '../stores/project'
import { useTasksStore } from '../stores/tasks'

export type NovelBatchRunContext = {
  outline: Record<string, any> | null
  assets: Array<{ name: string; size?: number }>
  chapterCountTotal: number
  engineReady: boolean
  semanticSearchEffective: boolean
  vectorEnabled: boolean
  arcProgress: Record<string, any> | null
  batchPaused: boolean
  pauseReason: string
  lastChapterId: string
}

const dialogVisible = ref(false)
/** 打开弹窗前拉取开书清单上下文 */
const opening = ref(false)
/** 同步卷队列 + 提交连写任务（可能多次 LLM，耗时较长） */
const running = ref(false)
let runAbort: AbortController | null = null
const form = ref({ target_chapters: 5, autopilot: true })
const ctx = ref<NovelBatchRunContext>({
  outline: null,
  assets: [],
  chapterCountTotal: 0,
  engineReady: false,
  semanticSearchEffective: true,
  vectorEnabled: true,
  arcProgress: null,
  batchPaused: false,
  pauseReason: '',
  lastChapterId: '',
})

function resolveEngine(config: any, models: any[]) {
  const llm = config?.llm || {}
  const modelsById = new Map(models.map((m: any) => [m.id, m]))
  const defaultId = llm.daily_model_id || llm.default_model_id || llm.default?.model_ref
  const defaultModel = defaultId ? modelsById.get(defaultId) : null
  if (defaultModel) return { ready: true }
  if (llm.default?.provider && llm.default.provider !== 'static') return { ready: true }
  if (llm.provider && llm.provider !== 'static') return { ready: true }
  return { ready: false }
}

export function useNovelBatchRun() {
  const router = useRouter()
  const projectStore = useProjectStore()
  const tasksStore = useTasksStore()
  const { currentProject } = storeToRefs(projectStore)

  const maxAvailableChapters = computed(() => {
    const outline = ctx.value.outline
    const profile = outline?.scale_profile || {}
    const scale = profile.scale || ''
    const hardMax = Number(profile.max_chapters) || 0
    const limit =
      outline?.target_chapters || currentProject.value?.target_chapters || hardMax || 20
    const cap =
      hardMax >= 999999 || scale === 'infinite'
        ? limit
        : Math.min(limit, hardMax || limit)
    return Math.max(0, cap - (ctx.value.chapterCountTotal || 0))
  })

  const workScale = computed(() => String(ctx.value.outline?.scale_profile?.scale || ''))

  const readinessItems = computed(() =>
    buildReadinessItems({
      engineReady: ctx.value.engineReady,
      outline: ctx.value.outline,
      assets: ctx.value.assets,
      maxAvailableChapters: maxAvailableChapters.value,
      semanticSearchEffective: ctx.value.semanticSearchEffective,
      vectorEnabled: ctx.value.vectorEnabled,
      workScale: workScale.value,
    }),
  )

  const canRun = computed(() => readinessAllOk(readinessItems.value))

  const isCircuitPaused = computed(
    () =>
      ctx.value.batchPaused &&
      (ctx.value.pauseReason || 'circuit_breaker') === 'circuit_breaker',
  )

  const dialogTitle = computed(() =>
    ctx.value.batchPaused ? '继续写书' : '连写启动',
  )

  /** 粗估：单章全流水线约 8k–15k tokens（规划+写作+审校），取 12k 中位 */
  const TOKENS_PER_CHAPTER_ESTIMATE = 12_000

  const tokenEstimate = computed(() => {
    const n = Math.min(form.value.target_chapters || 0, maxAvailableChapters.value || 0)
    if (n <= 0) return { chapters: 0, tokens: 0, label: '—' }
    const tokens = n * TOKENS_PER_CHAPTER_ESTIMATE
    const label =
      tokens >= 1_000_000
        ? `约 ${(tokens / 1_000_000).toFixed(1)}M tokens`
        : tokens >= 1000
          ? `约 ${Math.round(tokens / 1000)}k tokens`
          : `约 ${tokens} tokens`
    return { chapters: n, tokens, label }
  })

  const REFRESH_TIMEOUT_MS = 45_000

  function withRefreshTimeout<T>(promise: Promise<T>, label: string): Promise<T> {
    return Promise.race([
      promise,
      new Promise<never>((_, reject) => {
        setTimeout(
          () => reject(new Error(`${label}超时，请确认栖墨后台已启动（日志中心可看日志）`)),
          REFRESH_TIMEOUT_MS,
        )
      }),
    ])
  }

  async function refreshContext() {
    const [assetRes, countRes, outlineRes, modelsRes, configRes, embRes, arcRes, batchRes] =
      await withRefreshTimeout(
        Promise.all([
          listAssets().catch(() => ({ data: [] })),
          getChapterCount(true).catch(() => ({ data: { total: 0 } })),
          getOutline().catch(() => ({ data: {} })),
          listModels().catch(() => ({ data: [] })),
          getConfig().catch(() => ({ data: {} })),
          getEmbeddingStatus().catch(() => ({ data: {} })),
          getArcProgress().catch(() => ({ data: { progress: null } })),
          getNovelBatchStatus().catch(() => ({ data: {} })),
        ]),
        '加载开书状态',
      )
    const outlineData = outlineRes.data
    const progress = arcRes.data?.progress || batchRes.data || null
    ctx.value = {
      outline: outlineData && Object.keys(outlineData).length > 0 ? outlineData : null,
      assets: assetRes.data || [],
      chapterCountTotal: countRes.data?.total ?? 0,
      engineReady: resolveEngine(configRes.data, modelsRes.data || []).ready,
      semanticSearchEffective: Boolean(embRes.data?.semantic_search_effective),
      vectorEnabled: embRes.data?.vector_enabled !== false,
      arcProgress: progress,
      batchPaused: progress?.status === 'paused',
      pauseReason: String(progress?.pause_reason || ''),
      lastChapterId: String(progress?.last_chapter_id || ''),
    }
  }

  function applyFormDefaults() {
    form.value.autopilot = workScale.value !== 'micro'
    form.value.target_chapters = Math.min(5, maxAvailableChapters.value)
    if (workScale.value === 'long') {
      form.value.target_chapters = Math.min(10, maxAvailableChapters.value)
    } else if (workScale.value === 'epic' || workScale.value === 'infinite') {
      form.value.target_chapters = Math.min(10, maxAvailableChapters.value)
      form.value.autopilot = true
    } else if (workScale.value === 'micro' || workScale.value === 'short') {
      form.value.target_chapters = maxAvailableChapters.value
      form.value.autopilot = false
    }
    if (form.value.autopilot && maxAvailableChapters.value > 0) {
      form.value.target_chapters = maxAvailableChapters.value
    }
  }

  function warnIfNotReady(): boolean {
    if (canRun.value) return true
    const pending = readinessItems.value.filter((i) => !i.ok).map((i) => i.label)
    ElMessage.warning(`请先完成开书清单：${pending.join('、')}`)
    return false
  }

  function cancelBatchRun() {
    if (!runAbort) return
    runAbort.abort()
    runAbort = null
    opening.value = false
    running.value = false
    ElMessage.info('已取消连写启动')
  }

  /** 不经弹窗直接开跑（程序化入口）；界面按钮应走 openDialog → submit */
  async function startBatchRun() {
    if (busy.value) return
    opening.value = true
    try {
      await refreshContext()
    } catch (error: any) {
      ElMessage.error(error?.message || '无法加载开书状态，请稍后重试')
      return
    } finally {
      opening.value = false
    }
    if (!warnIfNotReady()) return
    applyFormDefaults()
    await submit(false)
  }

  /** 可选：调整本次章数 / 是否自动续轮后再启动 */
  async function openDialog() {
    if (busy.value) return
    opening.value = true
    try {
      await refreshContext()
    } catch (error: any) {
      ElMessage.error(error?.message || '无法加载开书状态，请稍后重试')
      return
    } finally {
      opening.value = false
    }
    if (!warnIfNotReady()) return
    applyFormDefaults()
    dialogVisible.value = true
  }

  function goMonitorAlerts() {
    dialogVisible.value = false
    router.push('/chapters/maintenance')
  }

  function goChapterRepair() {
    const ch = ctx.value.lastChapterId
    dialogVisible.value = false
    if (ch) {
      router.push(`/chapters/${ch}`)
      return
    }
    goMonitorAlerts()
  }

  async function submit(forceResume = false) {
    if (form.value.target_chapters <= 0) {
      ElMessage.warning('可生成章节数必须大于 0')
      return
    }
    if (form.value.target_chapters > maxAvailableChapters.value) {
      ElMessage.warning(
        `本次不能超过大纲剩余上限（最多 ${maxAvailableChapters.value} 章）`,
      )
      return
    }

    if (isCircuitPaused.value && !forceResume) {
      try {
        await ElMessageBox.confirm(
          `第 ${ctx.value.lastChapterId || '—'} 章因质量熔断暂停了全书批量。建议先在章节详情或写作页改稿并重跑门禁，再续写。仍要继续将跳过人工确认直接续跑。`,
          '质量熔断暂停',
          {
            confirmButtonText: '仍要继续写书',
            cancelButtonText: '先去改稿',
            type: 'warning',
            distinguishCancelAndClose: true,
          },
        )
        forceResume = true
      } catch {
        goChapterRepair()
        return
      }
    }

    running.value = true
    runAbort = new AbortController()
    const signal = runAbort.signal
    tasksStore.startRuntimeLogPolling()
    tasksStore.startPolling()
    let queueMsg: ReturnType<typeof ElMessage.info> | null = null
    try {
      queueMsg = ElMessage.info({
        message:
          '正在同步卷队列（首次约 1～5 分钟）。可点「取消连写」，或打开日志中心看任务流水。',
        duration: 0,
        showClose: true,
      })
      await ensureNovelQueue({ timeout: 600_000, signal })
      queueMsg?.close()
      queueMsg = null
      const cap = form.value.target_chapters
      const { data } = await continueNovel(
        {
          resume: true,
          max_chapters: cap,
          dry_run: false,
          autopilot: form.value.autopilot,
          full_book: true,
          force_resume: forceResume,
        },
        { signal },
      )
      const mode = form.value.autopilot ? '后台自动续轮' : '单轮'
      ElMessage.success(
        `已启动${mode}（上限 ${cap} 章，任务 ${data?.task_id || ''}），请到日志中心查看任务流水。`,
      )
      dialogVisible.value = false
      return data
    } catch (error: any) {
      if (signal.aborted || error?.code === 'ERR_CANCELED' || error?.name === 'CanceledError') {
        return
      }
      const detail = error?.response?.data?.detail
      const status = error?.response?.status
      const msg =
        typeof detail === 'string' && detail.trim()
          ? detail
          : status === 499
            ? '同步卷队列已取消'
            : error?.code === 'ECONNABORTED'
              ? '同步卷队列超时（模型过慢或未响应）。请检查设置中的 API，或到日志中心查看任务流水。'
              : error.message || '启动失败'
      ElMessage.error(msg)
      throw error
    } finally {
      queueMsg?.close()
      runAbort = null
      running.value = false
    }
  }

  const busy = computed(() => opening.value || running.value)

  return {
    dialogVisible,
    opening,
    running,
    busy,
    form,
    ctx,
    currentProject,
    maxAvailableChapters,
    workScale,
    readinessItems,
    canRun,
    isCircuitPaused,
    dialogTitle,
    tokenEstimate,
    refreshContext,
    startBatchRun,
    cancelBatchRun,
    openDialog,
    submit,
    goMonitorAlerts,
    goChapterRepair,
  }
}