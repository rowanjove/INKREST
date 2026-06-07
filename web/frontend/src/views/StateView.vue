<script setup lang="ts">
import { useRouter } from 'vue-router'
import { Calendar, Compass, Connection, Location, Refresh, Share } from '@element-plus/icons-vue'
import { useStateViewSettings } from '../composables/useStateViewSettings'
import { useStateViewChronicle } from '../composables/useStateViewChronicle'
import { NODE_CIRCLE_R, RELATION_TYPE_COLORS } from '../composables/useStateRelationGraph'
import { emotionDotColor } from '../utils/stateViewFilters'

const router = useRouter()

const {
  state,
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
} = useStateViewSettings()

const {
  activeOuterTab,
  activeTimelineTab,
  chronicleRefreshing,
  timelinePageSize,
  timelineEventPage,
  timelineFsPage,
  timelineHookPage,
  timelineNodePage,
  timelineEvents,
  timelineForeshadows,
  timelineHooks,
  timelineNodes,
  chapterGoalPreviews,
  showChapterGoalPreview,
  chronicleStats,
  refreshChronicle,
  paginatedTimelineEvents,
  paginatedTimelineForeshadows,
  paginatedTimelineHooks,
  paginatedTimelineNodes,
  characters,
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
  relationForm,
  openAddRelation,
  openEditRelation,
  submitRelation,
  deleteRelation,
} = useStateViewChronicle({ state, chapterRange, loadState })

const goChapters = () => router.push('/chapters')
const goMonitor = () => router.push('/monitor')
const goSettingsTab = () => {
  activeOuterTab.value = 'settings'
}
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
