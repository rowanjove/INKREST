import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { collectDebt, getState, searchEvents } from '../api'
import {
  matchesChapterRange,
  maxChapterFromState,
  sliderMarksFromMax,
} from '../utils/stateViewFilters'

const PAGE_SIZE = 12

export function useStateViewSettings() {
  const state = ref<any>(null)
  const events = ref<any[]>([])
  const eventQuery = ref('')
  const loadError = ref('')

  const activeTab = ref('characters')

  const charPage = ref(1)
  const forePage = ref(1)
  const hookPage = ref(1)
  const objPage = ref(1)
  const eventPage = ref(1)
  const pageSize = PAGE_SIZE

  const chapterRange = ref<[number, number]>([1, 1])
  const sliderInitialized = ref(false)

  const maxChapter = computed(() => maxChapterFromState(state.value))

  const sliderMarks = computed(() => sliderMarksFromMax(maxChapter.value))

  const matchesRange = (item: any) => matchesChapterRange(item, chapterRange.value)

  const loadState = async (sync = false) => {
    try {
      loadError.value = ''
      const { data } = await getState({ sync })
      state.value = data
      events.value = data.events || []

      if (!sliderInitialized.value && maxChapter.value > 0) {
        chapterRange.value = [1, maxChapter.value]
        sliderInitialized.value = true
      }
    } catch (error: any) {
      loadError.value = error.message || '状态库加载失败'
    }
  }

  const handleCollect = async (debtType: string, debtId: string) => {
    try {
      await collectDebt({ debt_type: debtType, debt_id: debtId, priority: 3 })
      ElMessage.success('催收成功！该伏笔已加入下一章强行注入计划中。')
      await loadState()
    } catch (error: any) {
      ElMessage.error(error.message || '催收失败')
    }
  }

  const handleSearch = async () => {
    try {
      loadError.value = ''
      const { data } = await searchEvents(eventQuery.value)
      events.value = data
    } catch (error: any) {
      loadError.value = error.message || '事件搜索失败'
    }
  }

  const filteredCharacters = computed(() => {
    if (!state.value) return []
    return Object.entries(state.value.characters).map(([id, d]: any) => ({ id, ...d }))
  })

  const filteredForeshadows = computed(() => {
    if (!state.value) return []
    return (state.value.foreshadows || []).filter(matchesRange)
  })

  const filteredHooks = computed(() => {
    if (!state.value) return []
    return (state.value.hooks || []).filter(matchesRange)
  })

  const filteredObjects = computed(() => {
    if (!state.value) return []
    return state.value.objects || []
  })

  const filteredEvents = computed(() => events.value.filter(matchesRange))

  const paginatedCharacters = computed(() => {
    const list = filteredCharacters.value
    const maxPage = Math.max(1, Math.ceil(list.length / pageSize))
    if (charPage.value > maxPage) charPage.value = 1
    return list.slice((charPage.value - 1) * pageSize, charPage.value * pageSize)
  })

  const paginatedForeshadows = computed(() => {
    const list = filteredForeshadows.value
    const maxPage = Math.max(1, Math.ceil(list.length / pageSize))
    if (forePage.value > maxPage) forePage.value = 1
    return list.slice((forePage.value - 1) * pageSize, forePage.value * pageSize)
  })

  const paginatedHooks = computed(() => {
    const list = filteredHooks.value
    const maxPage = Math.max(1, Math.ceil(list.length / pageSize))
    if (hookPage.value > maxPage) hookPage.value = 1
    return list.slice((hookPage.value - 1) * pageSize, hookPage.value * pageSize)
  })

  const paginatedObjects = computed(() => {
    const list = filteredObjects.value
    const maxPage = Math.max(1, Math.ceil(list.length / pageSize))
    if (objPage.value > maxPage) objPage.value = 1
    return list.slice((objPage.value - 1) * pageSize, objPage.value * pageSize)
  })

  const paginatedEvents = computed(() => {
    const list = filteredEvents.value
    const maxPage = Math.max(1, Math.ceil(list.length / pageSize))
    if (eventPage.value > maxPage) eventPage.value = 1
    return list.slice((eventPage.value - 1) * pageSize, eventPage.value * pageSize)
  })

  return {
    state,
    events,
    eventQuery,
    loadError,
    activeTab,
    charPage,
    forePage,
    hookPage,
    objPage,
    eventPage,
    pageSize,
    chapterRange,
    maxChapter,
    sliderMarks,
    loadState,
    handleCollect,
    handleSearch,
    filteredCharacters,
    filteredForeshadows,
    filteredHooks,
    filteredObjects,
    filteredEvents,
    paginatedCharacters,
    paginatedForeshadows,
    paginatedHooks,
    paginatedObjects,
    paginatedEvents,
  }
}