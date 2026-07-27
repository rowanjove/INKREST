import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { LocationQueryRaw } from 'vue-router'
import { getProductionWorkspace } from '../api/production'
import type {
  ProductionTab,
  ProductionWorkspace,
} from '../entities/production/production'
import { subscribePolling, unsubscribePolling } from '../utils/pollingHub'

const TABS = new Set<ProductionTab>(['runs', 'reviews', 'costs', 'logs'])
const POLL_KEY = 'production-workspace'

function routeTab(value: unknown): ProductionTab {
  return typeof value === 'string' && TABS.has(value as ProductionTab)
    ? (value as ProductionTab)
    : 'runs'
}

export function useProductionWorkspace() {
  const route = useRoute()
  const router = useRouter()
  const workspace = ref<ProductionWorkspace | null>(null)
  const loading = ref(false)
  const error = ref('')
  const activeTab = ref<ProductionTab>(routeTab(route.query.tab))
  const selectedTaskId = ref(
    typeof route.query.task === 'string' ? route.query.task : '',
  )
  const selectedChapterId = ref(
    typeof route.query.chapter === 'string' ? route.query.chapter : '',
  )
  let request: Promise<void> | null = null

  const selectedTask = computed(
    () =>
      workspace.value?.tasks.find((task) => task.id === selectedTaskId.value) ||
      workspace.value?.tasks[0] ||
      null,
  )
  const selectedReview = computed(
    () =>
      workspace.value?.reviews.items.find(
        (item) => item.chapter_id === selectedChapterId.value,
      ) ||
      workspace.value?.reviews.items[0] ||
      null,
  )

  async function load(options: { silent?: boolean } = {}) {
    if (request) return request
    if (!options.silent) loading.value = true
    error.value = ''
    request = getProductionWorkspace()
      .then(({ data }) => {
        workspace.value = data
        if (
          !selectedTaskId.value ||
          !data.tasks.some((task) => task.id === selectedTaskId.value)
        ) {
          selectedTaskId.value = data.tasks[0]?.id || ''
        }
        if (
          !selectedChapterId.value ||
          !data.reviews.items.some(
            (item) => item.chapter_id === selectedChapterId.value,
          )
        ) {
          selectedChapterId.value = data.reviews.items[0]?.chapter_id || ''
        }
      })
      .catch((reason: unknown) => {
        error.value =
          reason instanceof Error ? reason.message : '生产中心加载失败'
      })
      .finally(() => {
        request = null
        loading.value = false
      })
    return request
  }

  function syncQuery() {
    const query: LocationQueryRaw = { ...route.query, tab: activeTab.value }
    if (activeTab.value === 'runs' && selectedTaskId.value) {
      query.task = selectedTaskId.value
      delete query.chapter
    } else if (activeTab.value === 'reviews' && selectedChapterId.value) {
      query.chapter = selectedChapterId.value
      delete query.task
    } else {
      delete query.task
      delete query.chapter
    }
    void router.replace({ path: '/production', query })
  }

  watch([activeTab, selectedTaskId, selectedChapterId], syncQuery)
  watch(
    () => route.query.tab,
    (value) => {
      activeTab.value = routeTab(value)
    },
  )

  onMounted(() => {
    subscribePolling(POLL_KEY, () => load({ silent: true }), 4000)
  })
  onUnmounted(() => unsubscribePolling(POLL_KEY))

  return {
    workspace,
    loading,
    error,
    activeTab,
    selectedTaskId,
    selectedChapterId,
    selectedTask,
    selectedReview,
    load,
  }
}
