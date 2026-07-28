import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  generateOutline,
  getOutline,
  getCurrentProject,
  updateOutline,
  getArcQueueStale,
  markArcQueueSynced,
  apiErrorMessage,
  ensureNovelQueue,
} from '../api'
import { useTasksStore } from '../stores/tasks'
import { useOutlineMindmap } from './useOutlineMindmap'

export function useOutlineView() {
  const tasksStore = useTasksStore()
  const loading = ref(false)
  const submitting = ref(false)
  const outline = ref<Record<string, any> | null>(null)
  const project = ref<any>(null)
  const dialogVisible = ref(false)
  const editDialogVisible = ref(false)

  const viewMode = ref<'mindmap' | 'classic'>('classic')

  const form = ref({
    theme: '',
    genre: '',
    target_chapters: 20,
    special_requirements: '',
    overwrite: false,
  })

  const editForm = ref({
    title: '',
    logline: '',
    genre: '',
    core_theme: '',
    conflict: '',
    protagonist_name: '',
    protagonist_desire: '',
    protagonist_flaw: '',
    protagonist_edge: '',
    protagonist_limit: '',
  })

  const editGenesVisible = ref(false)
  const editGenesForm = ref({
    pleasure_mechanism: '',
    protagonist_arc: '',
    romance_weight: '',
    pacing_baseline: '',
    drift_guards: [] as string[],
  })
  const newGuard = ref('')
  const customTitle = ref('')

  const arcQueueStale = ref<{ stale?: boolean; message?: string } | null>(null)
  const arcSyncLoading = ref(false)

  const genreGenes = computed(() => outline.value?.genre_genes || {})

  const title = computed(() => {
    if (outline.value?.chosen_title) {
      return outline.value.chosen_title
    }
    return outline.value ? '【未确定最终小说名，请在上方选择】' : (project.value?.name || '未命名作品')
  })

  const logline = computed(() => outline.value?.logline || '还没有一句话梗概')
  const genre = computed(() => outline.value?.genre_positioning || project.value?.genre || '未设定')
  const protagonist = computed(() => outline.value?.protagonist || {})
  const arcs = computed(() => outline.value?.macro_outline || outline.value?.volume_arcs || outline.value?.arcs || [])
  const promises = computed(() => outline.value?.reader_promise || [])
  const targetChapters = computed(() => project.value?.target_chapters || form.value.target_chapters || 20)
  const displayIndex = (index: string | number) => Number(index) + 1

  const { connections, scheduleConnectionUpdate, setNodeRef } = useOutlineMindmap({
    viewMode,
    outline,
    arcs,
  })

  const loadArcStale = async () => {
    try {
      const { data } = await getArcQueueStale()
      arcQueueStale.value = data
    } catch {
      arcQueueStale.value = null
    }
  }

  const syncArcQueue = async () => {
    arcSyncLoading.value = true
    try {
      await ensureNovelQueue()
      await markArcQueueSynced()
      await loadArcStale()
      ElMessage.success('卷队列已按当前大纲同步')
    } catch (error: any) {
      ElMessage.error(apiErrorMessage(error, '同步卷队列失败'))
    } finally {
      arcSyncLoading.value = false
    }
  }

  const load = async () => {
    loading.value = true
    try {
      const [{ data: outlineData }, { data: projectData }] = await Promise.all([
        getOutline().catch(() => ({ data: {} })),
        getCurrentProject().catch(() => ({ data: null })),
      ])
      project.value = projectData
      outline.value = outlineData && Object.keys(outlineData).length ? outlineData : null
      form.value.theme = outline.value?.core_theme || projectData?.name || ''
      form.value.genre = outline.value?.genre_positioning || projectData?.genre || ''
      form.value.target_chapters = projectData?.target_chapters || 20

      if (viewMode.value === 'mindmap' && outline.value) {
        scheduleConnectionUpdate()
      }
      await loadArcStale()
    } finally {
      loading.value = false
    }
  }

  const submitOutline = async () => {
    if (!form.value.theme.trim()) {
      ElMessage.warning('先填写主题或核心卖点')
      return
    }
    submitting.value = true
    try {
      const { data } = await generateOutline(form.value)
      outline.value = data
      dialogVisible.value = false
      const staged = data.planning_staged ? '（长篇已分段生成卷纲）' : ''
      ElMessage.success(`大纲已生成并保存${staged}`)
      if (data.arc_queue_stale?.stale) {
        ElMessage.warning(data.arc_queue_stale.message || '请同步卷队列后再续跑')
      }
      if ((data.validation_warnings || []).length) {
        ElMessage.warning(data.validation_warnings.join('；'))
      }
      await loadArcStale()
      scheduleConnectionUpdate()
    } catch (error: any) {
      ElMessage.error(error?.response?.data?.detail || error.message || '大纲生成失败')
    } finally {
      submitting.value = false
    }
  }

  const openEditDialog = () => {
    const current = outline.value || {}
    const p = current.protagonist || {}
    const titles = current.title_options || []
    editForm.value = {
      title: current.chosen_title || (Array.isArray(titles) ? titles[0] || '' : String(titles || '')),
      logline: current.logline || '',
      genre: current.genre_positioning || project.value?.genre || '',
      core_theme: current.core_theme || '',
      conflict: current.conflict || '',
      protagonist_name: p.name || '',
      protagonist_desire: p.desire || '',
      protagonist_flaw: p.flaw || '',
      protagonist_edge: p.edge || '',
      protagonist_limit: p.limit || '',
    }
    editDialogVisible.value = true
  }

  const selectChosenTitle = async (selectedTitle: string) => {
    if (!selectedTitle || !selectedTitle.trim()) {
      ElMessage.warning('请输入或选择有效的书名')
      return
    }
    if (!outline.value) return

    loading.value = true
    try {
      const next = { ...outline.value }
      next.chosen_title = selectedTitle.trim()

      const { data } = await updateOutline(next)
      outline.value = data
      ElMessage.success(`书名已确定为「${selectedTitle}」`)
      window.location.reload()
    } catch (error: any) {
      ElMessage.error(error?.response?.data?.detail || error.message || '确定书名失败')
    } finally {
      loading.value = false
    }
  }

  const saveOutlineBasics = async () => {
    const next = { ...(outline.value || {}) }
    next.title_options = editForm.value.title ? [editForm.value.title] : []
    next.chosen_title = editForm.value.title || ''
    next.logline = editForm.value.logline
    next.genre_positioning = editForm.value.genre
    next.core_theme = editForm.value.core_theme
    next.conflict = editForm.value.conflict
    next.protagonist = {
      ...(next.protagonist || {}),
      name: editForm.value.protagonist_name,
      desire: editForm.value.protagonist_desire,
      flaw: editForm.value.protagonist_flaw,
      edge: editForm.value.protagonist_edge,
      limit: editForm.value.protagonist_limit,
    }
    try {
      const { data } = await updateOutline(next)
      outline.value = data
      editDialogVisible.value = false
      ElMessage.success('基础设定已保存')
      if (data.arc_queue_stale?.stale) {
        ElMessage.warning(data.arc_queue_stale.message || '卷纲已变更，请点「同步卷队列」')
      }
      await loadArcStale()
      await load()
    } catch (error: any) {
      ElMessage.error(error?.response?.data?.detail || error.message || '保存失败')
    }
  }

  const openEditGenes = () => {
    if (!outline.value) {
      ElMessage.warning('暂无小说大纲')
      return
    }
    const genes = genreGenes.value
    editGenesForm.value = {
      pleasure_mechanism: genes.pleasure_mechanism || '',
      protagonist_arc: genes.protagonist_arc || '',
      romance_weight: genes.romance_weight || '',
      pacing_baseline: genes.pacing_baseline || '',
      drift_guards: [...(genes.drift_guards || [])],
    }
    editGenesVisible.value = true
  }

  const addGuard = () => {
    if (newGuard.value.trim() && !editGenesForm.value.drift_guards.includes(newGuard.value.trim())) {
      editGenesForm.value.drift_guards.push(newGuard.value.trim())
      newGuard.value = ''
    }
  }

  const removeGuard = (tag: string) => {
    editGenesForm.value.drift_guards = editGenesForm.value.drift_guards.filter((g) => g !== tag)
  }

  const handleSaveGenes = async () => {
    loading.value = true
    try {
      const updatedOutline = {
        ...outline.value,
        genre_genes: {
          pleasure_mechanism: editGenesForm.value.pleasure_mechanism,
          protagonist_arc: editGenesForm.value.protagonist_arc,
          romance_weight: editGenesForm.value.romance_weight,
          pacing_baseline: editGenesForm.value.pacing_baseline,
          drift_guards: editGenesForm.value.drift_guards,
        },
      }
      await updateOutline(updatedOutline)
      ElMessage.success('类型基因修改成功')
      editGenesVisible.value = false
      await load()
    } catch (error: any) {
      ElMessage.error(error.message || '类型基因修改失败')
    } finally {
      loading.value = false
    }
  }

  onMounted(() => {
    void load()
  })

  return {
    tasksStore,
    loading,
    submitting,
    outline,
    project,
    dialogVisible,
    editDialogVisible,
    viewMode,
    form,
    editForm,
    editGenesVisible,
    editGenesForm,
    newGuard,
    customTitle,
    arcQueueStale,
    arcSyncLoading,
    genreGenes,
    title,
    logline,
    genre,
    protagonist,
    arcs,
    promises,
    targetChapters,
    displayIndex,
    connections,
    setNodeRef,
    load,
    syncArcQueue,
    submitOutline,
    openEditDialog,
    selectChosenTitle,
    saveOutlineBasics,
    openEditGenes,
    addGuard,
    removeGuard,
    handleSaveGenes,
  }
}