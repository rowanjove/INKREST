<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { Calendar, Compass, Connection, Location, Refresh, Share } from '@element-plus/icons-vue'
import { useStateStore } from '../stores/state'
import { useChapterStore } from '../stores/chapter'
import { 
  getState, searchEvents, collectDebt,
  getCharacterRelations, saveCharacterRelation, deleteCharacterRelation 
} from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const router = useRouter()
const chapterStore = useChapterStore()

// --- State View 原始核心数据 ---
const state = ref<any>(null)
const events = ref<any[]>([])
const eventQuery = ref('')
const loadError = ref('')

// Tabs active pane names
const activeOuterTab = ref('settings')
const activeTab = ref('characters')
const activeTimelineTab = ref('timeline')
const chronicleRefreshing = ref(false)

// Pagination states for settings
const charPage = ref(1)
const forePage = ref(1)
const hookPage = ref(1)
const objPage = ref(1)
const eventPage = ref(1)
const pageSize = 12

// Slider range filter state
const chapterRange = ref([1, 1])
const sliderInitialized = ref(false)

const loadState = async (sync = false) => {
  try {
    loadError.value = ''
    const { data } = await getState({ sync })
    state.value = data
    events.value = data.events || []
    
    // Automatically set range constraints on first load
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

// Compute the maximum chapter ID present in the dataset
const maxChapter = computed(() => {
  let maxVal = 1
  const check = (id: any) => {
    if (!id) return
    const num = parseInt(id)
    if (!isNaN(num) && num > maxVal) {
      maxVal = num
    }
  }
  if (state.value) {
    ;(state.value.foreshadows || []).forEach((x: any) => check(x.chapter_id))
    ;(state.value.hooks || []).forEach((x: any) => check(x.chapter_id))
    ;(state.value.events || []).forEach((x: any) => check(x.chapter_id))
  }
  return maxVal
})

// Marks for el-slider
const sliderMarks = computed(() => {
  const marks: any = {
    1: '第 1 章',
  }
  if (maxChapter.value > 1) {
    marks[maxChapter.value] = `第 ${maxChapter.value} 章`
  }
  return marks
})

// Helper filter function
const matchesChapterRange = (item: any) => {
  if (!item || !item.chapter_id) return true
  const num = parseInt(item.chapter_id)
  if (isNaN(num)) return true
  return num >= chapterRange.value[0] && num <= chapterRange.value[1]
}

// Computed Filtered Lists
const filteredCharacters = computed(() => {
  if (!state.value) return []
  return Object.entries(state.value.characters).map(([id, d]: any) => ({ id, ...d }))
})

const filteredForeshadows = computed(() => {
  if (!state.value) return []
  return (state.value.foreshadows || []).filter(matchesChapterRange)
})

const filteredHooks = computed(() => {
  if (!state.value) return []
  return (state.value.hooks || []).filter(matchesChapterRange)
})

const filteredObjects = computed(() => {
  if (!state.value) return []
  return state.value.objects || []
})

const filteredEvents = computed(() => {
  return events.value.filter(matchesChapterRange)
})

// Computed Paginated Lists
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

// --- 时空编年史 & 图谱数据 ---
const stateStore = useStateStore()
const { timeline, continuity } = storeToRefs(stateStore)
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

/** 编年史统一数据源：优先使用 loadState 结果，避免与 pinia 静默失败不同步 */
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

const timelineData = computed(() => timeline.value || { nodes: [], edges: [], foreshadows: [], hooks: [] })

const mergeById = (items: any[]) => {
  const map = new Map<string, any>()
  for (const item of items) {
    if (!item?.id) continue
    map.set(String(item.id), { ...map.get(String(item.id)), ...item })
  }
  return Array.from(map.values())
}

const timelineNodes = computed(() => {
  const nodes = (timelineData.value.nodes || []).filter(matchesChapterRange)
  return nodes.sort((a: any, b: any) => (parseInt(a.chapter_id) || 0) - (parseInt(b.chapter_id) || 0))
})

const timelineForeshadows = computed(() => {
  const fromState = (chronicleSource.value?.foreshadows || []).filter(matchesChapterRange)
  const fromTimeline = (timelineData.value.foreshadows || []).filter(matchesChapterRange)
  return mergeById([...fromState, ...fromTimeline]).sort(
    (a: any, b: any) => (parseInt(a.chapter_id) || 0) - (parseInt(b.chapter_id) || 0),
  )
})

const timelineHooks = computed(() => {
  const fromState = (chronicleSource.value?.hooks || []).filter(matchesChapterRange)
  const fromTimeline = (timelineData.value.hooks || []).filter(matchesChapterRange)
  return mergeById([...fromState, ...fromTimeline]).sort(
    (a: any, b: any) => (parseInt(a.chapter_id) || 0) - (parseInt(b.chapter_id) || 0),
  )
})

const timelineEvents = computed(() => {
  const events = (chronicleSource.value?.events || []).filter(matchesChapterRange)
  return events.sort((a: any, b: any) => (parseInt(a.chapter_id) || 0) - (parseInt(b.chapter_id) || 0))
})

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

const emotionDotColor = (emotion?: string) => {
  const e = emotion || ''
  return e.includes('怒') || e.includes('恨') ? 'var(--color-danger)' : 'var(--color-success)'
}

const goChapters = () => router.push('/chapters')
const goMonitor = () => router.push('/monitor')
const goSettingsTab = () => {
  activeOuterTab.value = 'settings'
}

// 分页切片计算
const paginatedTimelineEvents = computed(() => {
  const start = (timelineEventPage.value - 1) * timelinePageSize.value
  return timelineEvents.value.slice(start, start + timelinePageSize.value)
})

const paginatedTimelineForeshadows = computed(() => {
  const start = (timelineFsPage.value - 1) * timelinePageSize.value
  return timelineForeshadows.value.slice(start, start + timelinePageSize.value)
})

const paginatedTimelineHooks = computed(() => {
  const start = (timelineHookPage.value - 1) * timelinePageSize.value
  return timelineHooks.value.slice(start, start + timelinePageSize.value)
})

const paginatedTimelineNodes = computed(() => {
  const start = (timelineNodePage.value - 1) * timelinePageSize.value
  return timelineNodes.value.slice(start, start + timelinePageSize.value)
})

// --- 人物关系图谱：自动环形布局（无拖拽）---
const GRAPH_MIN_WIDTH = 880
const GRAPH_MIN_HEIGHT = 520
/** 圆点半径；连线和布局按此留白 */
const NODE_CIRCLE_R = 22
const NODE_EDGE_PAD = NODE_CIRCLE_R + 8
/** 相邻节点圆心最小弧长间距 */
const MIN_NODE_ARC_GAP = 96

type RelationPolarity = 'forward' | 'neutral' | 'reverse'

type GraphNode = {
  id: string
  name: string
  location: string
  emotion: string
  x: number
  y: number
}

type GraphEdge = {
  raw: any
  id: number | string
  sourceId: string
  targetId: string
  relation_type: string
  intensity: number
  description: string
  since_chapter: number
  polarity: RelationPolarity
  typeColor: string
  polarityColor: string
  x1: number
  y1: number
  x2: number
  y2: number
  midX: number
  midY: number
  label: string
}

const characters = computed(() => {
  const chars = chronicleSource.value?.characters
  if (!chars) return []
  return Object.entries(chars).map(([id, d]: any) => ({
    id,
    name: d.name || id,
    location: d.location || '',
    emotion: d.emotion || '',
  }))
})

const RELATION_TYPE_COLORS: Record<string, string> = {
  结盟: '#2563eb',
  合作: '#0891b2',
  师徒: '#c66f4f',
  同门: '#0d9488',
  亲属: '#7c3aed',
  恋人: '#db2777',
  暗恋: '#ec4899',
  敌对: '#dc2626',
  反目: '#b91c1c',
  竞争: '#ea580c',
}

const polarityFromIntensity = (intensity: number): RelationPolarity => {
  if (intensity > 0.15) return 'forward'
  if (intensity < -0.15) return 'reverse'
  return 'neutral'
}

const polarityColor = (polarity: RelationPolarity) => {
  if (polarity === 'forward') return '#16a34a'
  if (polarity === 'reverse') return '#dc2626'
  return '#94a3b8'
}

const colorForRelationType = (type: string) => {
  const key = (type || '').trim()
  if (key && RELATION_TYPE_COLORS[key]) return RELATION_TYPE_COLORS[key]
  let hash = 0
  for (let i = 0; i < key.length; i++) hash = key.charCodeAt(i) + ((hash << 5) - hash)
  const hue = Math.abs(hash) % 360
  return `hsl(${hue}, 52%, 42%)`
}

const resolveCharacterId = (key: string, charList: { id: string; name: string }[]) => {
  if (!key) return null
  if (charList.some((c) => c.id === key)) return key
  const byName = charList.find((c) => c.name === key)
  return byName?.id ?? key
}

const truncateGraphName = (name: string, maxLen = 4) => {
  const s = (name || '').trim()
  if (s.length <= maxLen) return s
  return `${s.slice(0, maxLen)}…`
}

const layoutRadiusForCount = (n: number, maxR: number) => {
  if (n <= 1) return 0
  const byGap = MIN_NODE_ARC_GAP / (2 * Math.sin(Math.PI / n))
  return Math.min(maxR, Math.max(118, byGap))
}

const edgeLinePoints = (sx: number, sy: number, tx: number, ty: number, pad = NODE_EDGE_PAD) => {
  const dx = tx - sx
  const dy = ty - sy
  const dist = Math.sqrt(dx * dx + dy * dy) || 1
  const ux = dx / dist
  const uy = dy / dist
  return {
    x1: sx + ux * pad,
    y1: sy + uy * pad,
    x2: tx - ux * pad,
    y2: ty - uy * pad,
    midX: (sx + tx) / 2,
    midY: (sy + ty) / 2,
  }
}

const graphLayout = computed(() => {
  const charList = characters.value
  const rels = relations.value
  const nodeIds = new Set<string>()

  for (const c of charList) nodeIds.add(c.id)
  for (const r of rels) {
    if (r.source_char) nodeIds.add(resolveCharacterId(r.source_char, charList) || r.source_char)
    if (r.target_char) nodeIds.add(resolveCharacterId(r.target_char, charList) || r.target_char)
  }

  const nodes: GraphNode[] = Array.from(nodeIds).map((id) => {
    const fromChar = charList.find((c) => c.id === id || c.name === id)
    return {
      id: fromChar?.id ?? id,
      name: fromChar?.name ?? id,
      location: fromChar?.location ?? '',
      emotion: fromChar?.emotion ?? '',
      x: 0,
      y: 0,
    }
  })

  const n = nodes.length
  const footprint = NODE_CIRCLE_R + 10
  const maxR = Math.min(GRAPH_MIN_WIDTH, GRAPH_MIN_HEIGHT) / 2 - footprint - 28
  const radius = layoutRadiusForCount(n, maxR)
  const canvasPad = 52
  const width = Math.max(GRAPH_MIN_WIDTH, 2 * (radius + footprint) + canvasPad * 2)
  const height = Math.max(GRAPH_MIN_HEIGHT, 2 * (radius + footprint) + canvasPad * 2)
  const cx = width / 2
  const cy = height / 2
  nodes.forEach((node, i) => {
    const angle = (2 * Math.PI * i) / Math.max(1, n) - Math.PI / 2
    node.x = cx + radius * Math.cos(angle)
    node.y = cy + radius * Math.sin(angle)
  })

  const nodeMap = new Map(nodes.map((nd) => [nd.id, nd]))
  const edges: GraphEdge[] = []

  for (const r of rels) {
    const sourceId = resolveCharacterId(r.source_char, charList)
    const targetId = resolveCharacterId(r.target_char, charList)
    if (!sourceId || !targetId || sourceId === targetId) continue
    const source = nodeMap.get(sourceId)
    const target = nodeMap.get(targetId)
    if (!source || !target) continue

    const intensity = Number(r.intensity ?? 0)
    const polarity = polarityFromIntensity(intensity)
    const pts = edgeLinePoints(source.x, source.y, target.x, target.y)
    const relationType = r.relation_type || '未命名'
    const polarityLabel =
      polarity === 'forward' ? '正向' : polarity === 'reverse' ? '反向' : '中立'

    edges.push({
      raw: r,
      id: r.id ?? `${sourceId}-${targetId}-${relationType}`,
      sourceId,
      targetId,
      relation_type: relationType,
      intensity,
      description: r.description || '',
      since_chapter: r.since_chapter || 1,
      polarity,
      typeColor: colorForRelationType(relationType),
      polarityColor: polarityColor(polarity),
      ...pts,
      label: `${relationType} · ${polarityLabel} (${intensity >= 0 ? '+' : ''}${intensity.toFixed(1)})`,
    })
  }

  return { nodes, edges, hasEdges: edges.length > 0, width, height }
})

const graphViewport = computed(() => ({
  width: graphLayout.value.width || GRAPH_MIN_WIDTH,
  height: graphLayout.value.height || GRAPH_MIN_HEIGHT,
}))

const hoveredEdge = ref<GraphEdge | null>(null)
const edgeTooltipStyle = ref({ left: '0px', top: '0px' })

const showEdgeTooltip = (edge: GraphEdge, event: MouseEvent) => {
  hoveredEdge.value = edge
  const wrap = (event.currentTarget as Element)?.closest?.('.svg-wrapper') as HTMLElement | null
  if (!wrap) return
  const rect = wrap.getBoundingClientRect()
  edgeTooltipStyle.value = {
    left: `${event.clientX - rect.left + 12}px`,
    top: `${event.clientY - rect.top + 12}px`,
  }
}

const hideEdgeTooltip = () => {
  hoveredEdge.value = null
}

const graphNodes = computed(() => graphLayout.value.nodes)
const graphEdges = computed(() => graphLayout.value.edges)
const graphHasRenderableNodes = computed(() => graphNodes.value.length > 0)

// 关系对话框
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const activeRelationId = ref<number | null>(null)
const relationForm = ref({
  source_char: '',
  target_char: '',
  relation_type: '',
  intensity: 0.5,
  since_chapter: 1,
  description: ''
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
    description: ''
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
    description: rel.description || ''
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
      type: 'warning'
    })
    await deleteCharacterRelation(activeRelationId.value)
    ElMessage.success('删除关系成功！')
    dialogVisible.value = false
    await refreshRelations()
  } catch (error: any) {
    if (error !== 'cancel') {
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
</script>

<template>
  <el-alert v-if="loadError" :title="loadError" type="warning" show-icon style="margin-bottom: 16px" />
  <div v-if="state">
    <header class="page-head">
      <div class="page-title-area">
        <h1>状态库</h1>
        <p>追踪小说角色属性、伏笔债务、物品状态以及时空编年史的发展脉络。</p>
      </div>
      <div class="page-actions">
        <el-button type="primary" :icon="Refresh" :loading="chronicleRefreshing" @click="refreshChronicle(false)">
          刷新载入
        </el-button>
      </div>
    </header>

    <el-tabs v-model="activeOuterTab" type="card" class="outer-state-tabs" style="margin-bottom: 20px;">
      <!-- Tab 1: 剧情设定库 -->
      <el-tab-pane label="📚 剧情设定库" name="settings">
        <!-- Global Chapter Filter Slider -->
        <el-card class="filter-card" style="margin-bottom: 20px; margin-top: 10px;">
          <template #header>
            <div class="card-header-flex">
              <span style="font-weight: bold; font-size: 15px">章节范围过滤</span>
              <span style="font-size: 13px; color: #909399">当前显示：第 {{ chapterRange[0] }} 章 至 第 {{ chapterRange[1] }} 章</span>
            </div>
          </template>
          <div style="padding: 0 10px 10px 10px">
            <el-slider
              v-model="chapterRange"
              range
              :min="1"
              :max="maxChapter"
              :marks="sliderMarks"
            />
          </div>
        </el-card>

        <!-- State Tabs -->
        <el-tabs v-model="activeTab" type="border-card" class="state-tabs">
          
          <!-- Characters Tab -->
          <el-tab-pane label="人物图鉴" name="characters">
            <el-table :data="paginatedCharacters" size="default" stripe style="width: 100%">
              <el-table-column prop="id" label="ID" width="120" />
              <el-table-column prop="name" label="姓名" width="150" />
              <el-table-column prop="location" label="当前位置" />
              <el-table-column prop="emotion" label="情绪" />
              <el-table-column prop="physical_state" label="身体状态" />
            </el-table>
            <div class="pagination-container">
              <el-pagination
                v-model:current-page="charPage"
                :page-size="pageSize"
                layout="total, prev, pager, next"
                :total="filteredCharacters.length"
              />
            </div>
          </el-tab-pane>

          <!-- Foreshadows Tab -->
          <el-tab-pane label="伏笔债务" name="foreshadows">
            <el-table :data="paginatedForeshadows" size="default" stripe style="width: 100%">
              <el-table-column prop="id" label="ID" width="100" />
              <el-table-column prop="title" label="标题" width="200" />
              <el-table-column prop="chapter_id" label="引入章节" width="100">
                <template #default="{ row }"> CH {{ row.chapter_id }} </template>
              </el-table-column>
              <el-table-column prop="deadline_chapter" label="回收截止章" width="120">
                <template #default="{ row }"> CH {{ row.deadline_chapter || '未设定' }} </template>
              </el-table-column>
              <el-table-column prop="status" label="回收状态" width="120">
                <template #default="{ row }">
                  <el-tag :type="row.status === 'open' ? 'danger' : row.status === 'resolved' ? 'success' : 'warning'" size="small">
                    {{ row.status === 'open' ? '待回收' : row.status === 'resolved' ? '已回收' : row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="tension_score" label="叙事张力值 (Tension)" width="180" sortable>
                <template #default="{ row }">
                  <div style="display: flex; align-items: center; gap: 8px">
                    <el-progress 
                      type="line" 
                      :percentage="Math.min(100, (row.tension_score || 0) * 4)" 
                      :status="row.alert ? 'exception' : 'warning'" 
                      :show-text="false"
                      style="width: 80px"
                    />
                    <span :style="{ color: row.alert ? '#F56C6C' : '#E6A23C', fontWeight: 'bold' }">
                      {{ row.tension_score || 0 }}
                    </span>
                    <el-tooltip v-if="row.alert" content="伏笔逾期未回收，面临红线警告！" placement="top">
                      <span style="cursor: pointer">⚠️</span>
                    </el-tooltip>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="description" label="详细描述" />
              <el-table-column label="操作" width="120">
                <template #default="{ row }">
                  <el-button 
                    v-if="row.status === 'open'" 
                    type="danger" 
                    size="small" 
                    plain
                    @click="handleCollect('foreshadow', row.id)"
                  >
                    强行催收
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
            <div class="pagination-container">
              <el-pagination
                v-model:current-page="forePage"
                :page-size="pageSize"
                layout="total, prev, pager, next"
                :total="filteredForeshadows.length"
              />
            </div>
          </el-tab-pane>

          <!-- Hooks Tab -->
          <el-tab-pane label="剧情钩子" name="hooks">
            <el-table :data="paginatedHooks" size="default" stripe style="width: 100%">
              <el-table-column prop="id" label="ID" width="100" />
              <el-table-column prop="title" label="标题" width="200" />
              <el-table-column prop="chapter_id" label="引入章节" width="100">
                <template #default="{ row }"> CH {{ row.chapter_id }} </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="100" />
              <el-table-column prop="description" label="描述" />
            </el-table>
            <div class="pagination-container">
              <el-pagination
                v-model:current-page="hookPage"
                :page-size="pageSize"
                layout="total, prev, pager, next"
                :total="filteredHooks.length"
              />
            </div>
          </el-tab-pane>

          <!-- Objects Tab -->
          <el-tab-pane label="道具线索" name="objects">
            <el-table :data="paginatedObjects" size="default" stripe style="width: 100%">
              <el-table-column prop="id" label="ID" width="100" />
              <el-table-column prop="name" label="名称" width="150" />
              <el-table-column prop="holder" label="持有者" width="150" />
              <el-table-column prop="status" label="状态" />
            </el-table>
            <div class="pagination-container">
              <el-pagination
                v-model:current-page="objPage"
                :page-size="pageSize"
                layout="total, prev, pager, next"
                :total="filteredObjects.length"
              />
            </div>
          </el-tab-pane>

          <!-- Events Tab -->
          <el-tab-pane label="历史事件簿" name="events">
            <div style="display: flex; justify-content: flex-end; align-items: center; margin-bottom: 16px; gap: 8px">
              <el-input v-model="eventQuery" placeholder="搜索事件..." size="default" style="width: 250px" @keyup.enter="handleSearch" clearable @clear="eventQuery = ''; loadState()" />
              <el-button type="primary" @click="handleSearch">搜索</el-button>
              <el-button @click="eventQuery = ''; loadState()">重置</el-button>
            </div>
            <el-table :data="paginatedEvents" size="default" stripe style="width: 100%">
              <el-table-column prop="id" label="ID" width="150" />
              <el-table-column prop="chapter_id" label="章节" width="100">
                <template #default="{ row }"> CH {{ row.chapter_id }} </template>
              </el-table-column>
              <el-table-column prop="scene_id" label="场景" width="100" />
              <el-table-column prop="summary" label="摘要" />
            </el-table>
            <div class="pagination-container">
              <el-pagination
                v-model:current-page="eventPage"
                :page-size="pageSize"
                layout="total, prev, pager, next"
                :total="filteredEvents.length"
              />
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-tab-pane>

      <!-- Tab 2: 时空编年史 -->
      <el-tab-pane label="🌌 时空编年史" name="chronicle">
        <div class="chronicle-root">
          <el-card class="chronicle-toolbar-card" shadow="never">
            <div class="chronicle-toolbar">
              <div class="chronicle-toolbar-left">
                <p class="chronicle-hint">
                  数据来自章节「设定同步」与状态库。写完章并跑完流水线后，事件、伏笔、钩子会自动入库。
                </p>
                <div class="chronicle-stats">
                  <el-tag type="info" effect="plain">事件 {{ chronicleStats.events }}</el-tag>
                  <el-tag type="warning" effect="plain">伏笔 {{ chronicleStats.foreshadows }}</el-tag>
                  <el-tag type="danger" effect="plain">钩子 {{ chronicleStats.hooks }}</el-tag>
                  <el-tag effect="plain">实体 {{ chronicleStats.nodes }}</el-tag>
                  <el-tag type="success" effect="plain">角色 {{ chronicleStats.characters }}</el-tag>
                </div>
              </div>
              <div class="chronicle-toolbar-right">
                <span class="chronicle-range-label">第 {{ chapterRange[0] }}–{{ chapterRange[1] }} 章</span>
                <el-slider
                  v-model="chapterRange"
                  range
                  :min="1"
                  :max="maxChapter"
                  style="width: 220px"
                  size="small"
                />
                <el-button :icon="Refresh" :loading="chronicleRefreshing" @click="refreshChronicle()">
                  刷新
                </el-button>
              </div>
            </div>
          </el-card>

          <el-tabs v-model="activeTimelineTab" type="border-card" class="state-tabs">
            
            <!-- Relations Graph Tab -->
            <el-tab-pane label="人物图谱" name="relations">
              <div class="tab-content-wrapper relations-container">
                <div class="toolbar relations-toolbar">
                  <span class="relations-hint">
                    节点自动环形排布；鼠标悬停连线查看关系，双击连线可编辑。线色=关系类型，箭头方向=好感正向/反向/中立。
                  </span>
                  <el-button type="primary" size="small" :icon="Share" @click="openAddRelation">新增人物关系</el-button>
                </div>

                <div v-if="graphHasRenderableNodes && graphEdges.length" class="relations-legend">
                  <span class="legend-title">好感方向</span>
                  <span class="legend-item"><i class="swatch forward" />正向（强度 &gt; 0.15）</span>
                  <span class="legend-item"><i class="swatch neutral" />中立</span>
                  <span class="legend-item"><i class="swatch reverse" />反向（强度 &lt; -0.15）</span>
                  <span class="legend-sep">|</span>
                  <span class="legend-title">常见关系色</span>
                  <span v-for="(color, label) in RELATION_TYPE_COLORS" :key="label" class="legend-item">
                    <i class="swatch" :style="{ background: color }" />{{ label }}
                  </span>
                </div>
                
                <div v-if="!graphHasRenderableNodes" class="empty-state">
                  <el-icon><Connection /></el-icon>
                  <p>暂无角色数据。章节生成后会自动写入人物状态；也可在「剧情设定库 → 人物图鉴」查看。</p>
                  <div class="empty-state-actions">
                    <el-button type="primary" @click="goChapters">去章节流水线</el-button>
                    <el-button @click="goSettingsTab">打开剧情设定库</el-button>
                  </div>
                </div>
                <div v-else class="svg-wrapper">
                  <svg
                    id="relations-svg"
                    class="relations-svg"
                    :viewBox="`0 0 ${graphViewport.width} ${graphViewport.height}`"
                    preserveAspectRatio="xMidYMid meet"
                  >
                    <defs>
                      <marker id="arrow-forward" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
                        <path d="M 0 0 L 10 5 L 0 10 z" fill="#16a34a" />
                      </marker>
                      <marker id="arrow-reverse" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
                        <path d="M 0 0 L 10 5 L 0 10 z" fill="#dc2626" />
                      </marker>
                    </defs>

                    <g v-for="edge in graphEdges" :key="'edge-' + edge.id" class="edge-group">
                      <line
                        :x1="edge.x1"
                        :y1="edge.y1"
                        :x2="edge.x2"
                        :y2="edge.y2"
                        class="edge-hit"
                        @mouseenter="showEdgeTooltip(edge, $event)"
                        @mousemove="showEdgeTooltip(edge, $event)"
                        @mouseleave="hideEdgeTooltip"
                        @dblclick="openEditRelation(edge.raw)"
                      />
                      <line
                        :x1="edge.polarity === 'reverse' ? edge.x2 : edge.x1"
                        :y1="edge.polarity === 'reverse' ? edge.y2 : edge.y1"
                        :x2="edge.polarity === 'reverse' ? edge.x1 : edge.x2"
                        :y2="edge.polarity === 'reverse' ? edge.y1 : edge.y2"
                        :stroke="edge.typeColor"
                        :stroke-width="2 + Math.min(4, Math.abs(edge.intensity) * 3)"
                        :stroke-dasharray="edge.polarity === 'neutral' ? '6 4' : undefined"
                        :opacity="hoveredEdge?.id === edge.id ? 1 : 0.82"
                        :marker-end="edge.polarity === 'forward' ? 'url(#arrow-forward)' : edge.polarity === 'reverse' ? 'url(#arrow-reverse)' : undefined"
                        class="edge-visible"
                        pointer-events="none"
                      />
                    </g>

                    <g
                      v-for="node in graphNodes"
                      :key="'node-' + node.id"
                      :transform="`translate(${node.x}, ${node.y})`"
                      class="graph-node"
                    >
                      <circle
                        :r="NODE_CIRCLE_R"
                        class="node-disk"
                        fill="var(--color-bg-surface)"
                        stroke="var(--color-primary)"
                        stroke-width="2"
                      />
                      <circle
                        r="5"
                        class="node-emotion-dot"
                        :cx="NODE_CIRCLE_R - 4"
                        :cy="-(NODE_CIRCLE_R - 4)"
                        :fill="emotionDotColor(node.emotion)"
                      />
                      <text class="node-name" text-anchor="middle" dominant-baseline="central">
                        {{ truncateGraphName(node.name) }}
                      </text>
                      <title>{{ node.name }} · {{ node.location || '未知位置' }} · {{ node.emotion || '平静' }}</title>
                    </g>
                  </svg>

                  <div
                    v-if="hoveredEdge"
                    class="edge-tooltip"
                    :style="edgeTooltipStyle"
                  >
                    <strong>{{ hoveredEdge.relation_type }}</strong>
                    <p>{{ hoveredEdge.label }}</p>
                    <p v-if="hoveredEdge.description">{{ hoveredEdge.description }}</p>
                    <p class="edge-tooltip-meta">
                      {{ hoveredEdge.raw.source_char }} → {{ hoveredEdge.raw.target_char }}
                      · 第 {{ hoveredEdge.since_chapter }} 章起
                    </p>
                    <p class="edge-tooltip-hint">双击连线可编辑</p>
                  </div>

                  <div v-if="graphNodes.length && !graphEdges.length" class="graph-no-edges-hint">
                    已有 {{ graphNodes.length }} 名角色，暂无关系连线。点击「新增人物关系」添加。
                  </div>
                </div>
              </div>
            </el-tab-pane>

            <!-- Timeline Events -->
            <el-tab-pane label="事件轴" name="timeline">
              <div class="tab-content-wrapper">
                <div v-if="timelineEvents.length === 0 && !showChapterGoalPreview" class="empty-state">
                  <el-icon><Calendar /></el-icon>
                  <p>暂无已入库事件。请先运行章节生成，并在章节详情确认「设定同步」已写入。</p>
                  <div class="empty-state-actions">
                    <el-button type="primary" @click="goChapters">去写章 / 跑流水线</el-button>
                    <el-button @click="goMonitor">查看日志中心</el-button>
                    <el-button :loading="chronicleRefreshing" @click="refreshChronicle()">重新拉取</el-button>
                  </div>
                </div>
                <div v-else-if="showChapterGoalPreview" class="chronicle-preview-block">
                  <el-alert
                    type="info"
                    :closable="false"
                    show-icon
                    title="以下为章节目标预览（尚未写入事件库）"
                    description="完成章节生成且状态提取成功后，这里会显示正式编年事件。"
                  />
                  <el-timeline class="chronicle-visual-timeline">
                    <el-timeline-item
                      v-for="evt in chapterGoalPreviews"
                      :key="evt.id"
                      :timestamp="`第 ${evt.chapter_id} 章`"
                      placement="top"
                      type="primary"
                      hollow
                    >
                      <p class="chronicle-timeline-summary">{{ evt.summary }}</p>
                    </el-timeline-item>
                  </el-timeline>
                  <div class="empty-state-actions">
                    <el-button type="primary" @click="goChapters">继续生成章节</el-button>
                  </div>
                </div>
                <div v-else class="table-container">
                  <el-timeline v-if="timelineEvents.length <= 40" class="chronicle-visual-timeline">
                    <el-timeline-item
                      v-for="evt in timelineEvents"
                      :key="evt.id"
                      :timestamp="`第 ${evt.chapter_id} 章`"
                      placement="top"
                    >
                      <p class="chronicle-timeline-summary">{{ evt.summary || '未定义事件' }}</p>
                      <p v-if="evt.consequences" class="event-desc-sub">{{ evt.consequences }}</p>
                      <div v-if="evt.characters?.length" class="tag-group chronicle-inline-tags">
                        <el-tag v-for="c in evt.characters" :key="c" size="small" type="success" effect="light" round>
                          {{ c }}
                        </el-tag>
                      </div>
                    </el-timeline-item>
                  </el-timeline>
                  <el-divider v-if="timelineEvents.length <= 40" content-position="left">表格视图</el-divider>
                  <el-table :data="paginatedTimelineEvents" style="width: 100%" stripe size="large">
                    <el-table-column prop="chapter_id" label="章节" width="120" align="center">
                      <template #default="scope">
                        <el-tag type="info" effect="dark" class="chapter-badge">
                          第 {{ scope.row.chapter_id }} 章
                        </el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column prop="summary" label="发生事件（大纲与起伏）" min-width="320">
                      <template #default="scope">
                        <div class="event-summary-text">{{ scope.row.summary || '未定义事件' }}</div>
                        <div v-if="scope.row.consequences" class="event-desc-sub">{{ scope.row.consequences }}</div>
                      </template>
                    </el-table-column>
                    <el-table-column label="登场角色" width="220">
                      <template #default="scope">
                        <div class="tag-group">
                          <el-tag
                            v-for="c in scope.row.characters"
                            :key="c"
                            size="small"
                            type="success"
                            effect="light"
                            round
                          >
                            {{ c }}
                          </el-tag>
                          <span v-if="!scope.row.characters?.length" class="empty-placeholder">-</span>
                        </div>
                      </template>
                    </el-table-column>
                    <el-table-column label="关联线索/物品" width="220">
                      <template #default="scope">
                        <div class="tag-group">
                          <el-tag
                            v-for="t in scope.row.threads"
                            :key="t"
                            size="small"
                            type="warning"
                            effect="plain"
                          >
                            {{ t }}
                          </el-tag>
                          <el-tag
                            v-for="o in scope.row.objects"
                            :key="o"
                            size="small"
                            type="danger"
                            effect="plain"
                          >
                            {{ o }}
                          </el-tag>
                          <span v-if="!scope.row.threads?.length && !scope.row.objects?.length" class="empty-placeholder">-</span>
                        </div>
                      </template>
                    </el-table-column>
                  </el-table>
                  
                  <div class="page-footer">
                    <el-pagination
                      background
                      layout="prev, pager, next, total"
                      :total="timelineEvents.length"
                      :page-size="timelinePageSize"
                      v-model:current-page="timelineEventPage"
                    />
                  </div>
                </div>
              </div>
            </el-tab-pane>

            <!-- Foreshadows -->
            <el-tab-pane label="伏笔线索" name="foreshadows">
              <div class="tab-content-wrapper">
                <div v-if="timelineForeshadows.length === 0" class="empty-state">
                  <el-icon><Compass /></el-icon>
                  <p>暂无伏笔数据。可在「剧情设定库 → 伏笔债务」查看全量列表。</p>
                  <div class="empty-state-actions">
                    <el-button @click="goSettingsTab">打开伏笔债务</el-button>
                    <el-button :loading="chronicleRefreshing" @click="refreshChronicle()">刷新</el-button>
                  </div>
                </div>
                <div v-else>
                  <div class="foreshadow-grid">
                    <div
                      v-for="f in paginatedTimelineForeshadows"
                      :key="f.id"
                      class="foreshadow-card"
                      :class="{ resolved: f.status === 'closed' || f.status === 'resolved' }"
                    >
                      <div class="fs-header">
                        <span class="fs-title">{{ f.title || f.id }}</span>
                        <el-tag :type="f.status === 'open' ? 'warning' : 'success'" size="small" effect="dark">
                          {{ f.status === 'open' ? '未回收' : '已回收' }}
                        </el-tag>
                      </div>
                      <p class="fs-content">{{ f.content || f.description }}</p>
                      <div class="fs-meta">
                        <span v-if="f.chapter_id">埋设: 第{{ f.chapter_id }}章</span>
                        <span v-if="f.deadline_chapter">回收窗口: 第{{ f.deadline_chapter }}章截止</span>
                        <span v-if="f.reveal_chapter">已在: 第{{ f.reveal_chapter }}章收尾</span>
                      </div>
                    </div>
                  </div>
                  <div class="page-footer">
                    <el-pagination
                      background
                      layout="prev, pager, next, total"
                      :total="timelineForeshadows.length"
                      :page-size="timelinePageSize"
                      v-model:current-page="timelineFsPage"
                    />
                  </div>
                </div>
              </div>
            </el-tab-pane>

            <!-- Hooks -->
            <el-tab-pane label="章节钩子" name="hooks">
              <div class="tab-content-wrapper">
                <div v-if="timelineHooks.length === 0" class="empty-state">
                  <el-icon><Connection /></el-icon>
                  <p>暂无章节钩子。钩子通常在章节审计阶段写入。</p>
                  <div class="empty-state-actions">
                    <el-button type="primary" @click="goChapters">去章节列表</el-button>
                  </div>
                </div>
                <div v-else>
                  <div class="hooks-grid">
                    <div v-for="h in paginatedTimelineHooks" :key="h.id" class="hook-card">
                      <div class="hook-header">
                        <span class="hook-chapter">第 {{ h.chapter_id }} 章</span>
                        <el-tag size="small" type="danger" effect="plain">{{ h.type || h.pressure_level || '留悬念' }}</el-tag>
                      </div>
                      <p class="hook-desc">{{ h.content || h.description }}</p>
                    </div>
                  </div>
                  <div class="page-footer">
                    <el-pagination
                      background
                      layout="prev, pager, next, total"
                      :total="timelineHooks.length"
                      :page-size="timelinePageSize"
                      v-model:current-page="timelineHookPage"
                    />
                  </div>
                </div>
              </div>
            </el-tab-pane>

            <!-- Nodes -->
            <el-tab-pane label="实体节点" name="nodes">
              <div class="tab-content-wrapper">
                <div v-if="timelineNodes.length === 0" class="empty-state">
                  <el-icon><Location /></el-icon>
                  <p>暂无地点/实体节点。章节状态提取会写入 timeline_nodes。</p>
                  <div class="empty-state-actions">
                    <el-button type="primary" @click="goMonitor">查看状态提取任务</el-button>
                  </div>
                </div>
                <div v-else>
                  <div class="nodes-grid">
                    <div v-for="node in paginatedTimelineNodes" :key="node.id" class="node-card">
                      <div class="node-header">
                        <span class="node-name">{{ node.label || node.name || node.id }}</span>
                        <span class="node-type">{{ node.type || node.kind || '实体' }}</span>
                      </div>
                      <p class="node-desc" v-if="node.description">{{ node.description }}</p>
                    </div>
                  </div>
                  <div class="page-footer">
                    <el-pagination
                      background
                      layout="prev, pager, next, total"
                      :total="timelineNodes.length"
                      :page-size="timelinePageSize"
                      v-model:current-page="timelineNodePage"
                    />
                  </div>
                </div>
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- Relation Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新增人物关系设定' : '修改人物关系设定'"
      width="450px"
      append-to-body
    >
      <el-form :model="relationForm" label-width="90px">
        <el-form-item label="源角色" required>
          <el-select v-model="relationForm.source_char" placeholder="请选择主导角色" style="width: 100%">
            <el-option
              v-for="char in characters"
              :key="char.id"
              :label="char.name"
              :value="char.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="目标角色" required>
          <el-select v-model="relationForm.target_char" placeholder="请选择关联角色" style="width: 100%">
            <el-option
              v-for="char in characters"
              :key="char.id"
              :label="char.name"
              :value="char.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="关系类型" required>
          <el-input v-model="relationForm.relation_type" placeholder="如：结盟、敌对、暗恋、反目等" />
        </el-form-item>
        <el-form-item label="好感度强度">
          <el-slider
            v-model="relationForm.intensity"
            :min="-1.0"
            :max="1.0"
            :step="0.1"
            :marks="{ '-1': '敌对', '0': '中立', '1': '友好' }"
          />
        </el-form-item>
        <el-form-item label="起效章节">
          <el-input-number v-model="relationForm.since_chapter" :min="1" />
        </el-form-item>
        <el-form-item label="详细关系原因">
          <el-input
            v-model="relationForm.description"
            type="textarea"
            :rows="3"
            placeholder="详细描述角色关系为什么会发生这种变化..."
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
          <div>
            <el-button
              v-if="dialogMode === 'edit'"
              type="danger"
              plain
              @click="deleteRelation"
            >
              删除关系
            </el-button>
          </div>
          <div>
            <el-button @click="dialogVisible = false">取消</el-button>
            <el-button type="primary" @click="submitRelation">确定</el-button>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
  <el-skeleton v-else :rows="10" animated />
</template>

<style scoped>
.card-header-flex {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.outer-state-tabs {
  background: transparent;
}

.state-tabs {
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 20px;
  padding: 10px 0;
}

.tab-content-wrapper {
  padding: 8px 0;
}

.table-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chapter-badge {
  font-weight: 700;
  letter-spacing: 0.5px;
}

.event-summary-text {
  font-size: 14px;
  color: var(--color-text-strong);
  font-weight: 600;
  line-height: 1.5;
}

.event-desc-sub {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-top: 4px;
  line-height: 1.4;
}

.tag-group {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.empty-placeholder {
  color: var(--color-text-subtle);
  font-size: 13px;
}

.page-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid var(--color-bg-hover);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  min-height: 240px;
  padding: 32px;
  color: var(--color-text-muted);
  text-align: center;
}

.empty-state .el-icon {
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border: 1px solid var(--color-border);
  border-radius: 50%;
  color: var(--color-text-subtle);
  font-size: 20px;
}

.empty-state p {
  margin: 0;
  font-size: 14px;
}

/* Foreshadow cards */
.foreshadow-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 14px;
  margin-bottom: 16px;
}

.foreshadow-card {
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-surface);
  border-left: 4px solid var(--color-warning);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 8px;
  transition: transform 0.2s, box-shadow 0.2s;
}

.foreshadow-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.05);
}

.foreshadow-card.resolved {
  border-left-color: var(--color-success);
  opacity: 0.85;
}

.fs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.fs-title {
  font-weight: 700;
  font-size: 14px;
  color: var(--color-text-strong);
}

.fs-content {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-muted);
  line-height: 1.5;
}

.fs-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 11px;
  color: var(--color-text-muted);
  background: var(--color-bg-surface-muted);
  padding: 4px 8px;
  border-radius: 4px;
}

/* Hook cards */
.hooks-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
  margin-bottom: 16px;
}

.hook-card {
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-surface);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
  transition: transform 0.2s, box-shadow 0.2s;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.hook-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.05);
}

.hook-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.hook-chapter {
  font-size: 13px;
  font-weight: 700;
  color: #c66f4f;
}

.hook-desc {
  margin: 0;
  font-size: 13px;
  color: var(--color-text);
  line-height: 1.5;
}

/* Node cards */
.nodes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 14px;
  margin-bottom: 16px;
}

.node-card {
  padding: 16px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-surface);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
  transition: transform 0.2s, box-shadow 0.2s;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.node-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.05);
}

.node-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.node-name {
  font-weight: 700;
  font-size: 14px;
  color: var(--color-text-strong);
}

.node-type {
  font-size: 11px;
  color: var(--color-text-muted);
  background: var(--color-bg-hover);
  padding: 2px 8px;
  border-radius: 4px;
}

.node-desc {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-muted);
  line-height: 1.5;
}

.chronicle-root {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.chronicle-toolbar-card :deep(.el-card__body) {
  padding: 14px 18px;
}

.chronicle-toolbar {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.chronicle-toolbar-left {
  flex: 1;
  min-width: 240px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.chronicle-hint {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-muted);
  line-height: 1.5;
}

.chronicle-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chronicle-toolbar-right {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.chronicle-range-label {
  font-size: 12px;
  color: var(--color-text-subtle);
  white-space: nowrap;
}

.empty-state-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  margin-top: 4px;
}

.chronicle-preview-block {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chronicle-visual-timeline {
  margin: 8px 0 0 4px;
  max-width: 920px;
}

.chronicle-timeline-summary {
  margin: 0;
  font-size: 14px;
  color: var(--color-text-strong);
  font-weight: 600;
  line-height: 1.5;
}

.chronicle-inline-tags {
  margin-top: 8px;
}

.relations-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}

.relations-hint {
  flex: 1;
  font-size: 13px;
  color: var(--color-text-muted);
  line-height: 1.5;
}

.relations-legend {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 14px;
  margin-bottom: 12px;
  padding: 10px 12px;
  border: 1px solid var(--color-border-subtle);
  border-radius: 8px;
  background: var(--color-bg-surface-muted);
  font-size: 12px;
  color: var(--color-text-muted);
}

.legend-title {
  font-weight: 700;
  color: var(--color-text-strong);
}

.legend-sep {
  color: var(--color-border);
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.legend-item .swatch {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 2px;
}

.legend-item .swatch.forward {
  background: #16a34a;
}

.legend-item .swatch.neutral {
  background: #94a3b8;
}

.legend-item .swatch.reverse {
  background: #dc2626;
}

.svg-wrapper {
  position: relative;
  width: 100%;
}

.relations-svg {
  width: 100%;
  height: auto;
  max-height: min(68vh, 640px);
  min-height: 360px;
  display: block;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-surface-muted);
}

.graph-node {
  cursor: default;
  pointer-events: none;
}

.graph-node .node-disk {
  pointer-events: all;
}

.graph-node .node-name {
  font-size: 11px;
  font-weight: 650;
  fill: var(--color-text-strong);
  pointer-events: none;
  user-select: none;
}

.graph-node .node-emotion-dot {
  pointer-events: none;
}

.edge-hit {
  stroke: transparent;
  stroke-width: 14;
  cursor: pointer;
}

.edge-visible {
  pointer-events: none;
  transition: opacity 0.15s ease;
}

.edge-tooltip {
  position: absolute;
  z-index: 5;
  max-width: 280px;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-surface);
  box-shadow: var(--shadow-card);
  pointer-events: none;
  font-size: 12px;
  line-height: 1.45;
  color: var(--color-text);
}

.edge-tooltip strong {
  display: block;
  font-size: 14px;
  color: var(--color-text-strong);
  margin-bottom: 4px;
}

.edge-tooltip p {
  margin: 0 0 4px;
}

.edge-tooltip-meta {
  color: var(--color-text-muted);
}

.edge-tooltip-hint {
  margin-top: 6px !important;
  color: var(--color-text-subtle);
  font-size: 11px;
}

.graph-no-edges-hint {
  margin: 12px auto 0;
  width: fit-content;
  max-width: 92%;
  padding: 8px 14px;
  border-radius: 8px;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  font-size: 12px;
  line-height: 1.45;
  color: var(--color-text-muted);
  box-shadow: var(--shadow-panel);
  text-align: center;
}
</style>
