<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Download, Refresh } from '@element-plus/icons-vue'
import { useFactoryStore } from '../../stores/factory'
import { useProjectStore } from '../../stores/project'
import { apiErrorMessage, batchExportProjects, switchProject } from '../../api'
import type { StudioBookSummary, StudioKanbanColumnId } from '../../types/studio'

const EMPTY_BOOKS_BY_COLUMN: Record<StudioKanbanColumnId, StudioBookSummary[]> = {
  empty: [],
  planning: [],
  ready: [],
  running: [],
  blocked: [],
  complete: [],
}
import { formatFactoryState } from '../../utils/factoryStatus'

const router = useRouter()
const factoryStore = useFactoryStore()
const projectStore = useProjectStore()
const exporting = ref(false)
const selectedIds = ref<string[]>([])

const studio = computed(() => factoryStore.studio)
const columns = computed(() => studio.value?.columns || [])
const booksByColumn = computed(
  () => studio.value?.books_by_column ?? EMPTY_BOOKS_BY_COLUMN,
)

const allSelected = computed({
  get: () => {
    const books = studio.value?.books || []
    return books.length > 0 && selectedIds.value.length === books.length
  },
  set: (value: boolean) => {
    selectedIds.value = value ? (studio.value?.books || []).map((b) => b.id) : []
  },
})

function toggleBook(id: string, checked: boolean) {
  if (checked) {
    if (!selectedIds.value.includes(id)) selectedIds.value.push(id)
    return
  }
  selectedIds.value = selectedIds.value.filter((item) => item !== id)
}

async function refresh() {
  try {
    await factoryStore.loadStudio()
  } catch (error: unknown) {
    ElMessage.error(apiErrorMessage(error, '工作室看板刷新失败'))
  }
}

async function openBook(book: StudioBookSummary) {
  try {
    await switchProject(book.id)
    await projectStore.fetchCurrent()
    await projectStore.fetchProjects()
    router.push('/workspace')
  } catch (error: unknown) {
    ElMessage.error(apiErrorMessage(error, '切换作品失败'))
  }
}

async function exportSelected() {
  if (!selectedIds.value.length) {
    ElMessage.warning('请先选择要导出的作品')
    return
  }
  exporting.value = true
  try {
    const response = await batchExportProjects(selectedIds.value)
    const blob = new Blob([response.data], { type: 'application/zip' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'inkrest-studio-batch-export.zip'
    link.click()
    URL.revokeObjectURL(url)
    ElMessage.success(`已导出 ${selectedIds.value.length} 本书`)
  } catch (error: unknown) {
    ElMessage.error(apiErrorMessage(error, '批量导出失败'))
  } finally {
    exporting.value = false
  }
}

onMounted(refresh)
</script>

<template>
  <section class="studio-board">
    <header class="studio-head">
      <div>
        <h2>工作室生产看板</h2>
        <p v-if="studio">
          共 {{ studio.summary.total }} 本 · 生产中 {{ studio.summary.running }} · 待修复 {{ studio.summary.blocked }}
        </p>
      </div>
      <div class="studio-actions">
        <el-checkbox v-model="allSelected">全选</el-checkbox>
        <el-button :icon="Refresh" plain @click="refresh">刷新</el-button>
        <el-button
          type="primary"
          :icon="Download"
          :loading="exporting"
          :disabled="!selectedIds.length"
          @click="exportSelected"
        >
          批量导出
        </el-button>
      </div>
    </header>

    <div v-if="factoryStore.studioLoading" class="studio-loading">加载中…</div>

    <div v-else class="studio-kanban">
      <article v-for="column in columns" :key="column.id" class="kanban-column">
        <header class="kanban-column-head">
          <strong>{{ column.label }}</strong>
          <span>{{ (booksByColumn[column.id] || []).length }}</span>
        </header>
        <div class="kanban-cards">
          <div
            v-for="book in booksByColumn[column.id] || []"
            :key="book.id"
            class="kanban-card"
            :class="{ active: book.id === studio?.active_project_id }"
          >
            <div class="kanban-card-top">
              <el-checkbox
                :model-value="selectedIds.includes(book.id)"
                @update:model-value="(val: boolean) => toggleBook(book.id, val)"
              />
              <button type="button" class="kanban-title" @click="openBook(book)">
                {{ book.name }}
              </button>
            </div>
            <p v-if="book.author_label" class="kanban-author">{{ book.author_label }}</p>
            <p class="kanban-meta">
              {{ formatFactoryState(book.factory_state) }}
              · {{ book.completed_chapters }}/{{ book.target_chapters || '—' }} 章
            </p>
            <p v-if="book.blocked_count" class="kanban-risk">待修复 {{ book.blocked_count }} 章</p>
          </div>
          <p v-if="!(booksByColumn[column.id] || []).length" class="kanban-empty">暂无</p>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.studio-board {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.studio-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.studio-head h2 {
  margin: 0 0 4px;
  font-size: 20px;
}

.studio-head p {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 13px;
}

.studio-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.studio-loading {
  padding: 24px;
  text-align: center;
  color: var(--color-text-muted);
}

.studio-kanban {
  display: grid;
  grid-template-columns: repeat(6, minmax(180px, 1fr));
  gap: 10px;
  overflow-x: auto;
  padding-bottom: 8px;
}

.kanban-column {
  min-width: 180px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-surface-muted);
  display: flex;
  flex-direction: column;
  max-height: 520px;
}

.kanban-column-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-bottom: 1px solid var(--color-border);
  font-size: 13px;
}

.kanban-cards {
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
}

.kanban-card {
  padding: 10px;
  border-radius: 8px;
  border: 1px solid var(--color-border);
  background: var(--color-bg-surface);
}

.kanban-card.active {
  border-color: rgba(0, 122, 255, 0.45);
  box-shadow: 0 0 0 1px rgba(0, 122, 255, 0.15);
}

.kanban-card-top {
  display: flex;
  align-items: flex-start;
  gap: 6px;
}

.kanban-title {
  border: none;
  background: transparent;
  padding: 0;
  text-align: left;
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text-strong);
  cursor: pointer;
}

.kanban-title:hover {
  color: var(--color-primary);
}

.kanban-author,
.kanban-meta,
.kanban-risk,
.kanban-empty {
  margin: 4px 0 0;
  font-size: 11px;
  color: var(--color-text-muted);
}

.kanban-risk {
  color: #c53030;
  font-weight: 600;
}

.kanban-empty {
  text-align: center;
  padding: 12px 0;
}
</style>