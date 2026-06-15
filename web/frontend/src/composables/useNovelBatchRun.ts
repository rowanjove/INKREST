import { computed, ref, watch } from 'vue'
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
  getNovelReadiness,
  getPipelineAlerts,
  getOutline,
  listAssets,
  listModels,
} from '../api'
import {
  applyBatchFormDefaults,
  cancelBatchRunMessage,
  computeRoundProgress,
  loadSavedBatchForm,
  mergeBatchForm,
  saveBatchForm,
  type BatchRunPhase,
} from '../utils/batchRunForm'
import {
  buildReadinessItems,
  mergeServerReadinessPending,
  readinessCanContinue,
  resolveVectorContextFromApis,
  type ServerReadinessSnapshot,
  type VectorReadinessContext,
} from '../utils/projectReadiness'
import { isExternalPending } from '../utils/pipelineAlertFilters'
import {
  estimateBatchTokenCost,
  resolveDailyModelPricePer1k,
} from '../utils/tokenCostEstimate'
import { useProjectStore } from '../stores/project'
import { useTasksStore } from '../stores/tasks'
import { needsRepairBeforeResume } from '../utils/batchPause'
import { notifyPipelineStarted } from '../utils/pipelineNotify'

export type NovelBatchRunContext = {
  outline: Record<string, any> | null
  assets: Array<{ name: string; size?: number }>
  chapterCountTotal: number
  engineReady: boolean
  vectorReadiness: VectorReadinessContext
  serverReadiness: ServerReadinessSnapshot
  arcProgress: Record<string, any> | null
  batchPaused: boolean
  pauseReason: string
  lastChapterId: string
  externalPendingCount: number
  blockContinueUntilExternal: boolean
}

const dialogVisible = ref(false)
/** 打开弹窗时拉取上下文失败，留在弹窗内展示而非秒关 */
const openError = ref('')
/** 弹窗刚打开时禁止遮罩/误触关闭 */
let dialogCloseGuardUntil = 0
const dialogInteractReady = ref(false)
let dialogInteractTimer: ReturnType<typeof setTimeout> | null = null

function closeBatchDialog() {
  dialogCloseGuardUntil = 0
  dialogInteractReady.value = false
  openError.value = ''
  if (dialogInteractTimer) {
    clearTimeout(dialogInteractTimer)
    dialogInteractTimer = null
  }
  dialogVisible.value = false
}

function armDialogOpenGuard() {
  dialogInteractReady.value = false
  dialogCloseGuardUntil = Date.now() + 700
  if (dialogInteractTimer) clearTimeout(dialogInteractTimer)
  dialogInteractTimer = setTimeout(() => {
    dialogInteractReady.value = true
    dialogInteractTimer = null
  }, 400)
}

function beforeDialogClose(done: () => void) {
  if (Date.now() < dialogCloseGuardUntil) return
  done()
}
/** 打开弹窗前拉取开书清单上下文 */
const opening = ref(false)
/** 同步卷队列 + 提交连写任务（可能多次 LLM，耗时较长） */
const running = ref(false)
let runAbort: AbortController | null = null
const form = ref({ target_chapters: 5, autopilot: true })
const runPhase = ref<BatchRunPhase>('idle')
const continueSubmitted = ref(false)
const roundStartChapterCount = ref(0)
const roundTargetChapters = ref(0)
let chapterCountPollTimer: ReturnType<typeof setInterval> | null = null
const modelPricePer1k = ref(0.0144)
const modelPriceLabel = ref('默认模型')

const ctx = ref<NovelBatchRunContext>({
  outline: null,
  assets: [],
  chapterCountTotal: 0,
  engineReady: false,
  vectorReadiness: resolveVectorContextFromApis({}, {}),
  serverReadiness: {},
  arcProgress: null,
  batchPaused: false,
  pauseReason: '',
  lastChapterId: '',
  externalPendingCount: 0,
  blockContinueUntilExternal: false,
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
    const fromServer = ctx.value.serverReadiness.remaining_chapters
    if (typeof fromServer === 'number' && Number.isFinite(fromServer)) {
      return Math.max(0, fromServer)
    }
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

  const readinessItems = computed(() => {
    const server = ctx.value.serverReadiness
    const base = buildReadinessItems({
      engineReady: ctx.value.engineReady,
      outline: ctx.value.outline,
      assets: ctx.value.assets,
      maxAvailableChapters: maxAvailableChapters.value,
      ...ctx.value.vectorReadiness,
      workScale: workScale.value,
      arcQueueStale: Boolean(server.arc_queue_stale?.stale),
    })
    return mergeServerReadinessPending(base, server.pending)
  })

  const canRun = computed(() =>
    readinessCanContinue({
      items: readinessItems.value,
      serverOk: ctx.value.serverReadiness.ok,
    }),
  )

  const isCircuitPaused = computed(
    () => ctx.value.batchPaused && needsRepairBeforeResume(ctx.value.pauseReason),
  )

  const isExternalBlockActive = computed(
    () =>
      ctx.value.blockContinueUntilExternal && ctx.value.externalPendingCount > 0,
  )

  const dialogTitle = computed(() =>
    ctx.value.batchPaused ? '继续写书' : '连写启动',
  )

  const tokenEstimate = computed(() => {
    const n = Math.min(form.value.target_chapters || 0, maxAvailableChapters.value || 0)
    const est = estimateBatchTokenCost(n, modelPricePer1k.value)
    const priceLabel =
      est.chapters > 0
        ? `${est.priceLabel}（${modelPriceLabel.value} · ¥${modelPricePer1k.value.toFixed(3)}/千 tokens）`
        : '—'
    return { ...est, priceLabel }
  })

  async function refreshContext() {
    const [assetRes, countRes, outlineRes, modelsRes, configRes, embRes, arcRes, batchRes, alertsRes, readyRes] =
      await Promise.all([
        listAssets().catch(() => ({ data: [] })),
        getChapterCount(true).catch(() => ({ data: { total: 0 } })),
        getOutline().catch(() => ({ data: {} })),
        listModels().catch(() => ({ data: [] })),
        getConfig().catch(() => ({ data: {} })),
        getEmbeddingStatus().catch(() => ({ data: {} })),
        getArcProgress().catch(() => ({ data: { progress: null } })),
        getNovelBatchStatus().catch(() => ({ data: {} })),
        getPipelineAlerts().catch(() => ({ data: { alerts: [] } })),
        getNovelReadiness().catch(() => ({ data: {} })),
      ])
    try {
      const outlineData = outlineRes.data
      const progress = arcRes.data?.progress || batchRes.data || null
      const pricing = resolveDailyModelPricePer1k(configRes.data, modelsRes.data || [])
      modelPricePer1k.value = pricing.pricePer1k
      modelPriceLabel.value = pricing.modelLabel
      ctx.value = {
        outline: outlineData && Object.keys(outlineData).length > 0 ? outlineData : null,
        assets: assetRes.data || [],
        // 与工作台 loadWorkbench 一致，避免 authoritative_completed 偏大导致弹窗被静默拦截
        chapterCountTotal: countRes.data?.total ?? 0,
        engineReady: resolveEngine(configRes.data, modelsRes.data || []).ready,
        vectorReadiness: resolveVectorContextFromApis(readyRes.data, embRes.data),
        serverReadiness: (readyRes.data || {}) as ServerReadinessSnapshot,
        arcProgress: progress,
        batchPaused: progress?.status === 'paused',
        pauseReason: String(progress?.pause_reason || ''),
        lastChapterId: String(progress?.last_chapter_id || ''),
        externalPendingCount: (alertsRes.data?.alerts || []).filter((item: { last_stage?: string }) =>
          isExternalPending(item),
        ).length,
        blockContinueUntilExternal: Boolean(
          configRes.data?.runtime?.block_continue_until_external_pass,
        ),
      }
    } catch (error: unknown) {
      const message =
        error instanceof Error ? error.message : '解析开书状态失败，请重试'
      throw new Error(message)
    }
  }

  async function loadDialogContext(): Promise<boolean> {
    openError.value = ''
    opening.value = true
    runPhase.value = 'opening'
    try {
      await refreshContext()
      applyFormDefaults()
      return true
    } catch (error: any) {
      const message = error?.message || '无法加载开书状态，请稍后重试'
      openError.value = message
      ElMessage.error(message)
      return false
    } finally {
      opening.value = false
      if (runPhase.value === 'opening') runPhase.value = 'idle'
    }
  }

  function applyFormDefaults() {
    const defaults = applyBatchFormDefaults(workScale.value, maxAvailableChapters.value)
    const projectId = currentProject.value?.id || ''
    const saved = loadSavedBatchForm(projectId)
    form.value = mergeBatchForm(defaults, saved, maxAvailableChapters.value)
  }

  const roundProgress = computed(() =>
    computeRoundProgress({
      roundTarget: roundTargetChapters.value,
      startChapterCount: roundStartChapterCount.value,
      currentChapterCount: ctx.value.chapterCountTotal,
    }),
  )

  const busyPhaseLabel = computed(() => {
    if (runPhase.value === 'opening') return '正在加载开书状态…'
    if (runPhase.value === 'syncing_queue') return '正在同步卷队列（首次约 1～5 分钟）…'
    if (runPhase.value === 'submitting_continue') return '正在提交连写任务…'
    return ''
  })

  function stopChapterCountPoll() {
    if (chapterCountPollTimer) {
      clearInterval(chapterCountPollTimer)
      chapterCountPollTimer = null
    }
  }

  function startChapterCountPoll() {
    stopChapterCountPoll()
    chapterCountPollTimer = setInterval(() => {
      getNovelBatchStatus()
        .then((res) => {
          const n = res.data?.progress_summary?.authoritative_completed
          if (typeof n === 'number') {
            ctx.value.chapterCountTotal = n
          }
        })
        .catch(() => {
          /* ignore poll errors */
        })
    }, 8000)
  }

  function warnIfNotReady(): boolean {
    if (canRun.value) return true
    const pending = readinessItems.value.filter((i) => !i.ok).map((i) => i.label)
    ElMessage.warning(`请先完成开书清单：${pending.join('、')}`)
    return false
  }

  function cancelBatchRun() {
    const phase = opening.value ? 'opening' : runPhase.value
    const submitted = continueSubmitted.value
    if (runAbort) {
      runAbort.abort()
      runAbort = null
    }
    opening.value = false
    running.value = false
    runPhase.value = 'idle'
    continueSubmitted.value = false
    stopChapterCountPoll()
    ElMessage.info(cancelBatchRunMessage(phase, submitted))
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
    // 必须先同步弹出，再在弹窗内加载；失败时保留弹窗供重试，不能秒关
    dialogVisible.value = true
    armDialogOpenGuard()
    const ok = await loadDialogContext()
    if (ok && !canRun.value) {
      const pending = readinessItems.value.filter((i) => !i.ok).map((i) => i.label)
      ElMessage.warning(
        pending.length
          ? `开书清单尚有未就绪项：${pending.join('、')}。可在弹窗内查看详情后再启动。`
          : '开书清单未全绿，请补齐后再确认连写。',
      )
    }
  }

  async function retryDialogContext() {
    if (opening.value || running.value) return
    armDialogOpenGuard()
    await loadDialogContext()
  }

  function goMonitorAlerts() {
    closeBatchDialog()
    router.push('/chapters/maintenance')
  }

  function goChapterRepair() {
    const ch = ctx.value.lastChapterId
    closeBatchDialog()
    if (ch) {
      router.push(`/chapters/${ch}`)
      return
    }
    goMonitorAlerts()
  }

  async function submit(forceResume = false) {
    if (!canRun.value) {
      warnIfNotReady()
      return
    }
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

    if (isExternalBlockActive.value) {
      ElMessage.warning(
        `尚有 ${ctx.value.externalPendingCount} 章待外审通过。请先到章节维护标记「外审已通过」，或在设置关闭「外审未过禁止续跑」。`,
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

    const projectId = currentProject.value?.id || ''
    saveBatchForm(projectId, {
      target_chapters: form.value.target_chapters,
      autopilot: form.value.autopilot,
    })
    roundStartChapterCount.value = ctx.value.chapterCountTotal
    roundTargetChapters.value = form.value.target_chapters
    continueSubmitted.value = false
    running.value = true
    runAbort = new AbortController()
    const signal = runAbort.signal
    startChapterCountPoll()
    tasksStore.addProgress({
      step: 'ensure_queue',
      status: 'running',
      chapter_id: '',
      timestamp: Date.now(),
    })
    let queueMsg: ReturnType<typeof ElMessage.info> | null = null
    try {
      runPhase.value = 'syncing_queue'
      queueMsg = ElMessage.info({
        message:
          '正在同步卷队列（首次约 1～5 分钟）。可点「取消连写」，或打开日志中心看任务流水。',
        duration: 0,
        showClose: true,
      })
      await ensureNovelQueue({ timeout: 600_000, signal })
      tasksStore.addProgress({
        step: 'ensure_queue',
        status: 'done',
        chapter_id: '',
        timestamp: Date.now(),
      })
      queueMsg?.close()
      queueMsg = null
      const cap = form.value.target_chapters
      runPhase.value = 'submitting_continue'
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
      continueSubmitted.value = true
      const mode = form.value.autopilot ? '后台自动续轮' : '单轮'
      ElMessage.success(
        `已启动${mode}（上限 ${cap} 章，任务 ${data?.task_id || ''}），请到日志中心查看任务流水。`,
      )
      await tasksStore.refreshTaskList()
      notifyPipelineStarted()
      closeBatchDialog()
      window.dispatchEvent(new CustomEvent('inkrest-batch-finished'))
      return data
    } catch (error: any) {
      if (signal.aborted || error?.code === 'ERR_CANCELED' || error?.name === 'CanceledError') {
        return
      }
      tasksStore.addProgress({
        step: 'ensure_queue',
        status: 'error',
        chapter_id: '',
        timestamp: Date.now(),
      })
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
      const aborted = signal.aborted
      runAbort = null
      running.value = false
      runPhase.value = 'idle'
      stopChapterCountPoll()
      if (aborted) {
        tasksStore.addProgress({
          step: 'ensure_queue',
          status: 'error',
          chapter_id: '',
          timestamp: Date.now(),
        })
      }
    }
  }

  const busy = computed(() => opening.value || running.value)

  watch(
    () => currentProject.value?.id,
    () => {
      roundStartChapterCount.value = 0
      roundTargetChapters.value = 0
    },
  )

  return {
    dialogVisible,
    openError,
    dialogInteractReady,
    beforeDialogClose,
    closeBatchDialog,
    opening,
    running,
    busy,
    runPhase,
    busyPhaseLabel,
    roundProgress,
    form,
    ctx,
    currentProject,
    maxAvailableChapters,
    workScale,
    readinessItems,
    canRun,
    isCircuitPaused,
    isExternalBlockActive,
    dialogTitle,
    tokenEstimate,
    refreshContext,
    startBatchRun,
    cancelBatchRun,
    openDialog,
    retryDialogContext,
    submit,
    goMonitorAlerts,
    goChapterRepair,
  }
}