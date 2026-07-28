import { computed, onMounted, ref } from 'vue'
import { getPlanningWorkspace } from '../api'
import {
  EMPTY_PLANNING_WORKSPACE,
  type PlanningEntity,
  type PlanningWorkspace,
} from '../entities/planning/planningWorkspace'

export function usePlanningWorkspace() {
  const workspace = ref<PlanningWorkspace>({ ...EMPTY_PLANNING_WORKSPACE })
  const loading = ref(false)
  const error = ref('')
  const selectedId = ref('')
  const query = ref('')

  const selectedEntity = computed(
    () => workspace.value.entities.find((entity) => entity.id === selectedId.value) || null,
  )

  const filteredEntities = computed(() => {
    const normalized = query.value.trim().toLowerCase()
    if (!normalized) return workspace.value.entities
    return workspace.value.entities.filter((entity) =>
      [entity.name, entity.summary, entity.kind].join(' ').toLowerCase().includes(normalized),
    )
  })

  const selectEntity = (entity: PlanningEntity | string | null) => {
    selectedId.value = typeof entity === 'string' ? entity : entity?.id || ''
  }

  const load = async () => {
    loading.value = true
    error.value = ''
    try {
      const { data } = await getPlanningWorkspace()
      workspace.value = data
      if (!selectedId.value && data.entities.length) selectedId.value = data.entities[0].id
    } catch (reason: any) {
      error.value = reason?.response?.data?.detail || reason?.message || '策划数据加载失败'
    } finally {
      loading.value = false
    }
  }

  onMounted(load)
  return {
    workspace,
    loading,
    error,
    selectedId,
    selectedEntity,
    query,
    filteredEntities,
    selectEntity,
    load,
  }
}
