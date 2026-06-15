import { computed, ref } from 'vue'
import { storeToRefs } from 'pinia'
import {
  getArcProgress,
  getCalibrationReport,
  getChapterCount,
  getConfig,
  getEmbeddingStatus,
  getNovelReadiness,
  getNarrativeDebt,
  getOutline,
  getScaleProfile,
  listAssets,
  listChapters,
  listModels,
} from '../api'
import { inferNextChapterId, resolveEngine } from '../utils/dashboardEngine'
import {
  resolveVectorContextFromApis,
  type VectorReadinessContext,
} from '../utils/projectReadiness'
import { useChapterStore } from '../stores/chapter'
import { useProjectStore } from '../stores/project'

export function useDashboardWorkbench() {
  const chapterStore = useChapterStore()
  const projectStore = useProjectStore()
  const { currentProject } = storeToRefs(projectStore)

  const assets = ref<any[]>([])
  const outline = ref<Record<string, any> | null>(null)
  const engineStatus = ref({
    ready: false,
    label: '未配置可用模型',
    route: 'default',
  })
  const vectorReadiness = ref<VectorReadinessContext>(resolveVectorContextFromApis({}, {}))
  const semanticSearchEffective = computed(() => vectorReadiness.value.semanticSearchEffective)
  const vectorEnabledForProject = computed(() => vectorReadiness.value.vectorEnabled)
  const form = ref({
    chapter_id: '',
    goal: '推进主线冲突，制造清晰的章节钩子，并同步人物状态。',
  })
  const outlineForm = ref({
    theme: '',
    genre: '',
    target_chapters: 20,
  })
  const chaptersList = ref<any[]>([])
  const chapterCountTotal = ref(0)
  const arcProgress = ref<Record<string, any> | null>(null)
  const debt = ref<Record<string, any[]>>({
    foreshadows: [],
    secrets: [],
    reader_promises: [],
  })
  const calibration = ref<Record<string, any>>({})
  const scaleProfile = ref<Record<string, any>>({})

  const outlineTheme = computed(
    () => outline.value?.core_theme || currentProject.value?.description || '',
  )
  const outlineGenre = computed(
    () => outline.value?.genre_positioning || currentProject.value?.genre || '',
  )
  const targetChapters = computed(
    () => currentProject.value?.target_chapters || outlineForm.value.target_chapters || 20,
  )
  const allDebt = computed(() => [
    ...(debt.value.foreshadows || []).map((item) => ({ ...item, kind: '伏笔' })),
    ...(debt.value.secrets || []).map((item) => ({ ...item, kind: '秘密' })),
    ...(debt.value.reader_promises || []).map((item) => ({ ...item, kind: '读者承诺' })),
  ])
  const workScale = computed(() => String(outline.value?.scale_profile?.scale || ''))
  const maxAvailableChapters = computed(() => {
    const profile = outline.value?.scale_profile || {}
    const scale = profile.scale || ''
    const hardMax = Number(profile.max_chapters) || 0
    const limit =
      outline.value?.target_chapters || currentProject.value?.target_chapters || hardMax || 20
    const cap = hardMax >= 999999 || scale === 'infinite' ? limit : Math.min(limit, hardMax || limit)
    const currentCount = chapterCountTotal.value || 0
    return Math.max(0, cap - currentCount)
  })

  async function loadControlData() {
    try {
      const [debtResp, calibrationResp, scaleResp] = await Promise.all([
        getNarrativeDebt().catch(() => ({ data: { foreshadows: [], secrets: [], reader_promises: [] } })),
        getCalibrationReport().catch(() => ({ data: {} })),
        getScaleProfile().catch(() => ({ data: {} })),
      ])
      debt.value = debtResp.data || { foreshadows: [], secrets: [], reader_promises: [] }
      calibration.value = calibrationResp.data || {}
      scaleProfile.value = scaleResp.data || {}
    } catch (e) {
      console.error('加载长篇控制数据失败:', e)
    }
  }

  async function refreshScaleArchitecture() {
    try {
      const [{ data: outlineData }, scaleResp] = await Promise.all([
        getOutline(),
        getScaleProfile().catch(() => ({ data: {} })),
      ])
      outline.value = outlineData && Object.keys(outlineData).length > 0 ? outlineData : null
      scaleProfile.value = scaleResp.data || {}
    } catch {
      /* ignore */
    }
  }

  async function loadWorkbench(loadSerialData?: () => Promise<void>) {
    await Promise.all([chapterStore.refreshAll(), projectStore.fetchCurrent()])
    try {
      const [
        { data: assetData },
        { data: chapters },
        { data: countData },
        { data: outlineData },
        { data: models },
        { data: config },
        embRes,
        readyRes,
      ] = await Promise.all([
        listAssets(),
        listChapters({ offset: 0, limit: 50, sync: true, include_gaps: false }),
        getChapterCount(true),
        getOutline(),
        listModels(),
        getConfig(),
        getEmbeddingStatus().catch(() => ({ data: {} })),
        getNovelReadiness().catch(() => ({ data: {} })),
      ])
      assets.value = assetData
      const chapterRows = chapters.items ?? chapters
      chaptersList.value = chapterRows
      chapterCountTotal.value = countData?.total ?? chapterRows.length
      form.value.chapter_id = inferNextChapterId(chapterRows)
      outline.value = outlineData && Object.keys(outlineData).length > 0 ? outlineData : null
      engineStatus.value = resolveEngine(config, models)
      vectorReadiness.value = resolveVectorContextFromApis(readyRes.data, embRes.data)
    } catch {
      assets.value = []
      chaptersList.value = []
    }

    outlineForm.value.theme = outlineTheme.value || currentProject.value?.name || ''
    outlineForm.value.genre = outlineGenre.value || '玄幻'
    outlineForm.value.target_chapters = targetChapters.value
    if (loadSerialData) {
      await loadSerialData()
    }
    await loadControlData()
    try {
      const { data } = await getArcProgress()
      arcProgress.value = data.progress || null
    } catch {
      arcProgress.value = null
    }
  }

  return {
    assets,
    outline,
    engineStatus,
    vectorReadiness,
    semanticSearchEffective,
    vectorEnabledForProject,
    form,
    outlineForm,
    chaptersList,
    chapterCountTotal,
    arcProgress,
    debt,
    calibration,
    scaleProfile,
    allDebt,
    outlineTheme,
    outlineGenre,
    targetChapters,
    workScale,
    maxAvailableChapters,
    loadWorkbench,
    loadControlData,
    refreshScaleArchitecture,
  }
}