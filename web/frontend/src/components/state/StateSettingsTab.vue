<script setup lang="ts">
const chapterRange = defineModel<[number, number]>('chapterRange', { required: true })
const activeTab = defineModel<string>('activeTab', { required: true })
const charPage = defineModel<number>('charPage', { required: true })
const forePage = defineModel<number>('forePage', { required: true })
const hookPage = defineModel<number>('hookPage', { required: true })
const objPage = defineModel<number>('objPage', { required: true })
const eventPage = defineModel<number>('eventPage', { required: true })
const eventQuery = defineModel<string>('eventQuery', { required: true })

defineProps<{
  maxChapter: number
  sliderMarks: Record<number, string>
  pageSize: number
  paginatedCharacters: any[]
  filteredCharactersTotal: number
  paginatedForeshadows: any[]
  filteredForeshadowsTotal: number
  paginatedHooks: any[]
  filteredHooksTotal: number
  paginatedObjects: any[]
  filteredObjectsTotal: number
  paginatedEvents: any[]
  filteredEventsTotal: number
  onCollect: (type: string, id: string) => void
  onSearch: () => void
  onLoadState: () => void
}>()
</script>


<template>
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
                :total="filteredCharactersTotal"
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
                    @click="onCollect('foreshadow', row.id)"
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
                :total="filteredForeshadowsTotal"
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
                :total="filteredHooksTotal"
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
                :total="filteredObjectsTotal"
              />
            </div>
          </el-tab-pane>

          <!-- Events Tab -->
          <el-tab-pane label="历史事件簿" name="events">
            <div style="display: flex; justify-content: flex-end; align-items: center; margin-bottom: 16px; gap: 8px">
              <el-input v-model="eventQuery" placeholder="搜索事件..." size="default" style="width: 250px" @keyup.enter="onSearch" clearable @clear="eventQuery = ''; onLoadState()" />
              <el-button type="primary" @click="onSearch">搜索</el-button>
              <el-button @click="eventQuery = ''; onLoadState()">重置</el-button>
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
                :total="filteredEventsTotal"
              />
            </div>
          </el-tab-pane>
        </el-tabs>
</template>

<style scoped>
.card-header-flex{
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.state-tabs{
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
}

.pagination-container{
  display: flex;
  justify-content: center;
  margin-top: 20px;
  padding: 10px 0;
}
</style>
