import { computed, onMounted, ref, watch, type Ref } from 'vue'
import { useRoute } from 'vue-router'
import { storeToRefs } from 'pinia'
import { ElMessage, ElMessageBox } from 'element-plus'
import { isMessageBoxDismissal } from '../utils/elementPlusServices'
import {
  deleteCharacterRelation,
  getCharacterRelations,
  saveCharacterRelation,
} from '../api'
import { useChapterStore } from '../stores/chapter'
import { useStateStore } from '../stores/state'
import { buildChronicleTimeline, paginateTimelineItems } from '../utils/stateViewFilters'
import { useStateRelationGraph } from './useStateRelationGraph'

export function useStateViewChronicle(deps: {
  state: Ref<any>
  chapterRange: Ref<[number, number]>
  loadState: (sync?: boolean) => Promise<void>
}) {
  const { state, chapterRange, loadState } = deps

  const route = useRoute()
  const chapterStore = useChapterStore()
  const stateStore = useStateStore()
  const { timeline, continuity } = storeToRefs(stateStore)

  const activeOuterTab = ref('settings')
  const activeTimelineTab = ref('timeline')
  const chronicleRefreshing = ref(false)

  const timelinePageSize = ref(10)
  const timelineEventPage = ref(1)
  const timelineFsPage = ref(1)
  const timelineHookPage = ref(1)
  const timelineNodePage = ref(1)

  const relations = ref<any[]>([])

  const refreshRelations = async () => {
    try {
      const { data } = await getCharacterRelations()
      relations.value = data
    } catch (error: any) {
      console.error('加载人物关系失败:', error)
    }
  }

  const chronicleSource = computed(() => {
    if (state.value) return state.value
    return {
      characters: continuity.value?.characters || {},
      events: continuity.value?.events || [],
      foreshadows: continuity.value?.foreshadows || [],
      hooks: continuity.value?.hooks || [],
      objects: continuity.value?.objects || [],
      threads: continuity.value?.threads || [],
    }
  })

  const timelineData = computed(
    () => timeline.value || { nodes: [], edges: [], foreshadows: [], hooks: [] },
  )

  const chronicleTimeline = computed(() =>
    buildChronicleTimeline({
      source: chronicleSource.value,
      timeline: timelineData.value,
      range: chapterRange.value,
    }),
  )

  const timelineNodes = computed(() => chronicleTimeline.value.nodes)
  const timelineForeshadows = computed(() => chronicleTimeline.value.foreshadows)
  const timelineHooks = computed(() => chronicleTimeline.value.hooks)
  const timelineEvents = computed(() => chronicleTimeline.value.events)

  const chapterGoalPreviews = computed(() =>
    (chapterStore.chapters || [])
      .filter((ch) => ch.goal?.trim())
      .map((ch) => ({
        id: `preview_${ch.chapter_id}`,
        chapter_id: ch.chapter_id,
        summary: ch.goal,
        characters: [] as string[],
        threads: [] as string[],
        objects: [] as string[],
        _preview: true,
      }))
      .sort((a, b) => (parseInt(a.chapter_id) || 0) - (parseInt(b.chapter_id) || 0)),
  )

  const showChapterGoalPreview = computed(
    () => timelineEvents.value.length === 0 && chapterGoalPreviews.value.length > 0,
  )

  const chronicleStats = computed(() => ({
    events: timelineEvents.value.length,
    foreshadows: timelineForeshadows.value.length,
    hooks: timelineHooks.value.length,
    nodes: timelineNodes.value.length,
    characters: Object.keys(chronicleSource.value?.characters || {}).length,
    relations: relations.value.length,
  }))

  const refreshChronicle = async (quiet = false) => {
    chronicleRefreshing.value = true
    try {
      await Promise.all([
        loadState(true),
        stateStore.refreshAll(),
        refreshRelations(),
        chapterStore.fetchChapters(),
      ])
      if (!quiet) ElMessage.success('状态库已刷新')
    } catch (error: any) {
      ElMessage.error(error.message || '状态库刷新失败')
    } finally {
      chronicleRefreshing.value = false
    }
  }

  const paginatedTimelineEvents = computed(() =>
    paginateTimelineItems(timelineEvents.value, timelineEventPage.value, timelinePageSize.value),
  )

  const paginatedTimelineForeshadows = computed(() =>
    paginateTimelineItems(timelineForeshadows.value, timelineFsPage.value, timelinePageSize.value),
  )

  const paginatedTimelineHooks = computed(() =>
    paginateTimelineItems(timelineHooks.value, timelineHookPage.value, timelinePageSize.value),
  )

  const paginatedTimelineNodes = computed(() =>
    paginateTimelineItems(timelineNodes.value, timelineNodePage.value, timelinePageSize.value),
  )

  const {
    characters,
    graphLayout,
    graphViewport,
    graphNodes,
    graphEdges,
    graphHasRenderableNodes,
    hoveredEdge,
    edgeTooltipStyle,
    showEdgeTooltip,
    hideEdgeTooltip,
    truncateGraphName,
  } = useStateRelationGraph({ chronicleSource, relations })

  const dialogVisible = ref(false)
  const dialogMode = ref<'create' | 'edit'>('create')
  const activeRelationId = ref<number | null>(null)
  const relationForm = ref({
    source_char: '',
    target_char: '',
    relation_type: '',
    intensity: 0.5,
    since_chapter: 1,
    description: '',
  })

  const openAddRelation = () => {
    dialogMode.value = 'create'
    activeRelationId.value = null
    relationForm.value = {
      source_char: '',
      target_char: '',
      relation_type: '',
      intensity: 0.5,
      since_chapter: 1,
      description: '',
    }
    dialogVisible.value = true
  }

  const openEditRelation = (rel: any) => {
    dialogMode.value = 'edit'
    activeRelationId.value = rel.id
    relationForm.value = {
      source_char: rel.source_char,
      target_char: rel.target_char,
      relation_type: rel.relation_type,
      intensity: rel.intensity,
      since_chapter: rel.since_chapter || 1,
      description: rel.description || '',
    }
    dialogVisible.value = true
  }

  const submitRelation = async () => {
    if (!relationForm.value.source_char || !relationForm.value.target_char) {
      ElMessage.warning('源角色和目标角色不能为空')
      return
    }
    if (relationForm.value.source_char === relationForm.value.target_char) {
      ElMessage.warning('不能对同一个角色建立关系')
      return
    }
    try {
      await saveCharacterRelation(relationForm.value)
      ElMessage.success('保存关系成功！')
      dialogVisible.value = false
      await refreshRelations()
    } catch (error: any) {
      ElMessage.error(error.message || '保存关系失败')
    }
  }

  const deleteRelation = async () => {
    if (!activeRelationId.value) return
    try {
      await ElMessageBox.confirm('确定要删除这条人物关系吗？', '提示', {
        type: 'warning',
      })
      await deleteCharacterRelation(activeRelationId.value)
      ElMessage.success('删除关系成功！')
      dialogVisible.value = false
      await refreshRelations()
    } catch (error: any) {
      if (!isMessageBoxDismissal(error)) {
        ElMessage.error(error.message || '删除关系失败')
      }
    }
  }

  watch(activeOuterTab, (tab) => {
    if (tab === 'chronicle') refreshChronicle(true)
  })

  watch(
    () => route.query.tab,
    (tab) => {
      if (tab === 'chronicle') activeOuterTab.value = 'chronicle'
    },
  )

  onMounted(async () => {
    if (route.query.tab === 'chronicle') activeOuterTab.value = 'chronicle'
    await loadState()
    await stateStore.refreshAll()
    await refreshRelations()
    await chapterStore.fetchChapters()
    if (activeOuterTab.value === 'chronicle') await refreshChronicle(true)
  })

  return {
    activeOuterTab,
    activeTimelineTab,
    chronicleRefreshing,
    timelinePageSize,
    timelineEventPage,
    timelineFsPage,
    timelineHookPage,
    timelineNodePage,
    relations,
    chronicleSource,
    timelineData,
    timelineNodes,
    timelineForeshadows,
    timelineHooks,
    timelineEvents,
    chapterGoalPreviews,
    showChapterGoalPreview,
    chronicleStats,
    refreshChronicle,
    paginatedTimelineEvents,
    paginatedTimelineForeshadows,
    paginatedTimelineHooks,
    paginatedTimelineNodes,
    characters,
    graphLayout,
    graphViewport,
    graphNodes,
    graphEdges,
    graphHasRenderableNodes,
    hoveredEdge,
    edgeTooltipStyle,
    showEdgeTooltip,
    hideEdgeTooltip,
    truncateGraphName,
    dialogVisible,
    dialogMode,
    activeRelationId,
    relationForm,
    openAddRelation,
    openEditRelation,
    submitRelation,
    deleteRelation,
  }
}
