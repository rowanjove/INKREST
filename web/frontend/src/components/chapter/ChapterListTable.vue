<script setup lang="ts">
import { CopyDocument, Delete, Edit, Plus, Search } from '@element-plus/icons-vue'
import type { Router } from 'vue-router'
import type { useTasksStore } from '../../stores/tasks'

defineProps<{
  router: Router
  tasksStore: ReturnType<typeof useTasksStore>
  pipelineAlerts: any[]
  chapters: any[]
  deletingId: string
  copyingId: string
  gateRerunId: string
  searchQuery: string
  selectedStatus: string
  currentPage: number
  pageSize: number
  filteredChapters: any[]
  paginatedChapters: any[]
  isGateBlockedChapter: (chapterId: string) => boolean
  onRerunGateOnly: (chapterId: string) => void
  onGoWriter: (chapterId: string) => void
  onCopyChapterTitle: (chapter: any) => void
  onCopyChapterBody: (chapter: any) => void
  onConfirmDelete: (chapter: any) => void
  onOpenRepairDialog: (chapter: any) => void
  getRiskTagType: (chapter: any) => string
}>()

const searchQueryModel = defineModel<string>('searchQuery', { required: true })
const selectedStatusModel = defineModel<string>('selectedStatus', { required: true })
const currentPageModel = defineModel<number>('currentPage', { required: true })
const pageSizeModel = defineModel<number>('pageSize', { required: true })
</script>

<template>
  <div class="filter-bar panel">
    <el-input
      v-model="searchQueryModel"
      placeholder="输入章节ID或名称模糊搜索..."
      clearable
      :prefix-icon="Search"
      class="search-input"
      @input="currentPageModel = 1"
    />
    <el-select
      v-model="selectedStatusModel"
      placeholder="生产状态"
      clearable
      class="filter-select"
      @change="currentPageModel = 1"
    >
      <el-option label="缺失断档" value="missing" />
      <el-option label="正文已就绪" value="done" />
      <el-option label="等待正文生成" value="pending" />
    </el-select>
  </div>

  <el-alert
    v-if="pipelineAlerts.length > 0"
    type="warning"
    :closable="false"
    show-icon
    title="有章节待改稿"
    class="pending-alert"
  >
    共 {{ pipelineAlerts.length }} 章未过内部门禁。请先在章节维护或下方「编辑」处理，再回工作台继续写书。
    <el-button type="warning" link style="margin-left: 8px" @click="router.push('/chapters/maintenance')">
      打开章节维护
    </el-button>
  </el-alert>

  <div class="chapters-table-wrapper panel">
    <el-table
      v-loading="deletingId !== ''"
      :data="paginatedChapters"
      style="width: 100%"
      row-key="chapter_id"
      class="custom-chapters-table"
    >
      <el-table-column label="章节编号" width="120">
        <template #default="{ row }">
          <span class="ch-num-tag" :class="{ missing: row.is_missing }">
            {{ row.chapter_id }}
          </span>
        </template>
      </el-table-column>

      <el-table-column label="章节名称" min-width="200">
        <template #default="{ row }">
          <span v-if="row.is_missing" class="ch-title-text missing">【数据缺失断档】</span>
          <div v-else class="title-copy-row">
            <span
              class="ch-title-text clickable-title"
              @click="router.push(`/chapters/${row.chapter_id}`)"
            >
              {{ row.title || '未命名章节' }}
            </span>
            <el-button
              type="primary"
              link
              size="small"
              :icon="CopyDocument"
              :loading="copyingId === row.chapter_id"
              title="复制标题"
              aria-label="复制标题"
              class="copy-icon-only"
              @click.stop="onCopyChapterTitle(row)"
            />
          </div>
        </template>
      </el-table-column>

      <el-table-column label="字数" width="120">
        <template #default="{ row }">
          <span v-if="!row.is_missing" class="wordcount-text">{{ row.word_count || 0 }} 字</span>
          <span v-else class="wordcount-text missing">—</span>
        </template>
      </el-table-column>

      <el-table-column label="审核风险" width="120">
        <template #default="{ row }">
          <el-tag size="small" :type="getRiskTagType(row)">
            {{ row.is_missing ? '待补齐' : (row.risk_level || '未审核') }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="生产状态" width="160">
        <template #default="{ row }">
          <span v-if="row.is_missing" class="state-txt missing">缺失断档</span>
          <span v-else-if="row.final_path" class="state-txt ready">正文已生成</span>
          <span v-else class="state-txt pending">等待正文</span>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="260" align="right">
        <template #default="{ row }">
          <div class="action-buttons-wrap">
            <template v-if="!row.is_missing">
              <el-button
                v-if="isGateBlockedChapter(row.chapter_id)"
                size="small"
                type="warning"
                plain
                :loading="gateRerunId === row.chapter_id"
                @click="onRerunGateOnly(row.chapter_id)"
              >
                只重跑门禁
              </el-button>
              <el-button
                class="chapter-edit-btn"
                size="small"
                type="primary"
                plain
                :icon="Edit"
                @click="onGoWriter(row.chapter_id)"
              >
                编辑
              </el-button>
              <el-button
                size="small"
                plain
                :icon="CopyDocument"
                :loading="copyingId === row.chapter_id"
                title="复制正文"
                @click="onCopyChapterBody(row)"
              >
                复制
              </el-button>
              <el-button
                size="small"
                type="danger"
                plain
                :icon="Delete"
                :loading="deletingId === row.chapter_id"
                :disabled="tasksStore.isRunning"
                @click="onConfirmDelete(row)"
              >
                删除
              </el-button>
            </template>
            <template v-else>
              <el-button
                size="small"
                type="primary"
                :icon="Plus"
                :disabled="tasksStore.isRunning"
                @click="onOpenRepairDialog(row)"
              >
                补齐流水线
              </el-button>
            </template>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-bar" v-if="filteredChapters.length > 0">
      <el-pagination
        v-model:current-page="currentPageModel"
        v-model:page-size="pageSizeModel"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        :total="filteredChapters.length"
      />
    </div>
    <div v-else-if="chapters.length > 0" class="no-results-alert">暂无符合筛选条件的章节</div>
    <div v-else class="empty-list-card">
      <h2>还没有章节数据</h2>
      <p>请在侧栏进入「工作台」启动「连写启动」后，此处会展示各章进度。</p>
    </div>
  </div>
</template>

<style scoped>
.pending-alert {
  margin: 0;
}

.filter-bar {
  display: flex;
  gap: 12px;
  padding: 16px;
  align-items: center;
}

.search-input {
  flex: 1;
}

.filter-select {
  width: 200px;
}

.chapters-table-wrapper {
  padding: 12px 18px;
}

.custom-chapters-table {
  --el-table-border-color: var(--color-bg-hover);
  --el-table-header-bg-color: var(--color-bg-surface-muted);
}

.ch-num-tag {
  font-family: monospace;
  font-weight: 700;
  color: #b66346;
  font-size: 14.5px;
}

.ch-num-tag.missing {
  color: var(--color-danger);
}

.title-copy-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.ch-title-text {
  font-weight: 600;
  color: var(--color-text-strong);
}

.ch-title-text.clickable-title {
  cursor: pointer;
  color: var(--primary);
}

.ch-title-text.clickable-title:hover {
  text-decoration: underline;
}

.ch-title-text.missing {
  color: var(--color-text-subtle);
  font-style: italic;
  font-weight: 400;
}

.wordcount-text {
  font-size: 13.5px;
  color: #4b5563;
}

.wordcount-text.missing {
  color: var(--color-border);
}

.state-txt {
  font-size: 13px;
  font-weight: 600;
}

.state-txt.missing {
  color: #f87171;
}

.state-txt.ready {
  color: var(--color-success);
}

.state-txt.pending {
  color: var(--color-warning);
}

.action-buttons-wrap {
  display: flex;
  gap: 6px;
  justify-content: flex-end;
}

.chapter-edit-btn.el-button--primary.is-plain {
  font-weight: 700;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 14px;
  border-top: 1px solid var(--color-border-subtle);
}

.no-results-alert {
  padding: 30px;
  text-align: center;
  color: var(--text-muted);
  font-size: 14px;
}

.empty-list-card {
  display: grid;
  place-items: start;
  gap: 10px;
  padding: 34px;
}

.empty-list-card h2,
.empty-list-card p {
  margin: 0;
}
</style>