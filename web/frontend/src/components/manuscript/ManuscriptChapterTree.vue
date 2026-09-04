<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useVirtualizer } from '@tanstack/vue-virtual'
import { Document, Search } from '@element-plus/icons-vue'
import type {
  ManuscriptChapter,
  ManuscriptChapterStatus,
} from '../../entities/manuscript/manuscript'

const props = defineProps<{
  chapters: ManuscriptChapter[]
  activeChapterId: string
  catalogTotal?: number
  catalogHasMore?: boolean
}>()

const emit = defineEmits<{
  select: [chapterId: string]
  search: [query: string, status: 'all' | ManuscriptChapterStatus]
  loadMore: []
}>()

const query = ref('')
const status = ref<'all' | ManuscriptChapterStatus>('all')
const scrollElement = ref<HTMLElement | null>(null)
let searchTimer: number | null = null

watch([query, status], () => {
  if (searchTimer !== null) window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(() => {
    emit('search', query.value, status.value)
  }, 200)
})

const filtered = computed(() => {
  const needle = query.value.trim().toLowerCase()
  return props.chapters.filter((chapter) => {
    if (status.value !== 'all' && chapter.status !== status.value) return false
    if (!needle) return true
    return `${chapter.chapter_id} ${chapter.title}`.toLowerCase().includes(needle)
  })
})

const virtualizer = useVirtualizer(
  computed(() => ({
    count: filtered.value.length,
    getScrollElement: () => scrollElement.value,
    estimateSize: () => 64,
    overscan: 8,
    getItemKey: (index: number) => filtered.value[index]?.chapter_id ?? index,
  })),
)

const virtualRows = computed(() => virtualizer.value.getVirtualItems())
const totalHeight = computed(() => virtualizer.value.getTotalSize())
</script>

<template>
  <aside class="chapter-tree" aria-label="章节目录">
    <header>
      <div>
        <p>正文目录</p>
        <strong>{{ catalogTotal ?? chapters.length }} 章</strong>
      </div>
    </header>

    <div class="chapter-filters">
      <el-input
        v-model="query"
        :prefix-icon="Search"
        placeholder="搜索章节"
        clearable
        aria-label="搜索章节"
      />
      <el-segmented
        v-model="status"
        :options="[
          { label: '全部', value: 'all' },
          { label: '草稿', value: 'draft' },
          { label: '成稿', value: 'ready' },
          { label: '需处理', value: 'attention' },
        ]"
        aria-label="按状态筛选章节"
      />
    </div>

    <div ref="scrollElement" class="chapter-scroll">
      <div
        v-if="filtered.length"
        class="virtual-list"
        :style="{ height: `${totalHeight}px` }"
      >
        <button
          v-for="row in virtualRows"
          :key="String(row.key)"
          type="button"
          class="chapter-row"
          :class="{ active: filtered[row.index]?.chapter_id === activeChapterId }"
          :style="{ transform: `translateY(${row.start}px)`, height: `${row.size}px` }"
          @click="emit('select', filtered[row.index]!.chapter_id)"
        >
          <el-icon><Document /></el-icon>
          <span class="chapter-copy">
            <strong>{{ filtered[row.index]!.title || `第 ${filtered[row.index]!.chapter_id} 章` }}</strong>
            <small>
              第 {{ filtered[row.index]!.chapter_id }} 章 ·
              {{ filtered[row.index]!.word_count }} 字
            </small>
          </span>
          <span class="status-dot" :class="filtered[row.index]!.status">
            {{ filtered[row.index]!.status_label }}
          </span>
        </button>
      </div>
      <el-empty v-else description="没有匹配的章节" :image-size="64" />
      <el-button
        v-if="catalogHasMore"
        class="load-more"
        text
        @click="emit('loadMore')"
      >
        加载更多
      </el-button>
    </div>
  </aside>
</template>

<style scoped>
.chapter-tree {
  height: 100%;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-surface);
}
.chapter-tree header {
  min-height: 66px;
  display: flex;
  align-items: center;
  padding: 0 var(--space-4);
  border-bottom: 1px solid var(--color-border);
}
.chapter-tree header div {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  width: 100%;
  gap: 12px;
}
.chapter-tree header p {
  margin: 0;
  color: var(--color-text-strong);
  font-size: 14px;
  font-weight: 800;
}
.load-more {
  width: 100%;
  margin: var(--space-2) 0;
}
.chapter-tree header strong {
  color: var(--color-text-muted);
  font-size: 11px;
}
.chapter-filters {
  display: grid;
  gap: 10px;
  padding: 12px;
  border-bottom: 1px solid var(--color-border-subtle);
}
.chapter-filters :deep(.el-segmented) {
  width: 100%;
  --el-segmented-item-selected-color: var(--color-primary-strong, #1d4ed8);
  --el-segmented-item-selected-bg-color: var(--color-primary-subtle, #eff6ff);
}
.chapter-filters :deep(.el-segmented__item.is-selected) {
  font-weight: 700;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  outline: 1px solid var(--color-primary, #3b82f6);
}
.chapter-scroll {
  position: relative;
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 8px;
}
.virtual-list {
  position: relative;
  width: 100%;
}
.chapter-row {
  position: absolute;
  inset-inline: 0;
  top: 0;
  width: 100%;
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr) auto;
  align-items: center;
  gap: 9px;
  padding: 8px 9px;
  border: 0;
  border-left: 3px solid transparent;
  border-radius: 8px;
  background: transparent;
  color: var(--color-text);
  text-align: left;
  cursor: pointer;
}
.chapter-row:hover {
  background: var(--color-bg-hover);
}
.chapter-row.active {
  border-left-color: var(--color-primary);
  background: var(--color-primary-soft);
}
.chapter-copy {
  min-width: 0;
  display: grid;
  gap: 4px;
}
.chapter-copy strong {
  overflow: hidden;
  color: var(--color-text-strong);
  font-size: 13.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.chapter-copy small {
  color: var(--color-text-muted);
  font-size: 12px;
}
.status-dot {
  padding: 3px 6px;
  border-radius: 99px;
  background: var(--color-bg-surface-muted);
  color: var(--color-text-muted);
  font-size: 11.5px;
  font-weight: 600;
}
.status-dot.ready { color: var(--color-success); }
.status-dot.attention { color: var(--color-warning); }
</style>
