<script setup lang="ts">
import { Search } from '@element-plus/icons-vue'
import type { ChapterSummary } from '../../composables/useReaderView'

defineProps<{
  chapters: ChapterSummary[]
  filteredChapters: ChapterSummary[]
  selectedId: string
}>()

const drawerVisible = defineModel<boolean>('drawerVisible', { required: true })
const catalogSearch = defineModel<string>('catalogSearch', { required: true })

const emit = defineEmits<{
  selectChapter: [chapterId: string]
}>()
</script>

<template>
  <el-drawer
    v-model="drawerVisible"
    title="📚 章节目录"
    direction="ltr"
    size="340px"
    custom-class="catalog-drawer"
  >
    <div class="catalog-content">
      <el-input
        v-model="catalogSearch"
        placeholder="搜索章节名或ID..."
        clearable
        :prefix-icon="Search"
        class="catalog-search-input"
      />

      <div class="catalog-stats">共计 {{ chapters.length }} 章</div>

      <el-scrollbar class="catalog-scroll-list">
        <div class="catalog-list">
          <button
            v-for="item in filteredChapters"
            :key="item.chapter_id"
            class="catalog-item"
            :class="{ active: selectedId === item.chapter_id }"
            @click="emit('selectChapter', item.chapter_id)"
          >
            <div class="catalog-item-main">
              <span class="catalog-num">CH {{ item.chapter_id }}</span>
              <span class="catalog-title">{{ item.title || '未命名章节' }}</span>
            </div>
            <span class="catalog-words">{{ item.word_count || 0 }} 字</span>
          </button>
        </div>
      </el-scrollbar>
    </div>
  </el-drawer>
</template>

<style scoped>
.catalog-content {
  display: flex;
  flex-direction: column;
  gap: 14px;
  height: 100%;
}

.catalog-search-input {
  width: 100%;
}

.catalog-stats {
  font-size: 13px;
  color: var(--text-muted);
  font-weight: 600;
  padding: 0 4px;
}

.catalog-scroll-list {
  flex: 1;
}

.catalog-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 4px;
}

.catalog-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 14px;
  border-radius: 8px;
  border: 1px solid var(--color-bg-hover);
  background: #fafafa;
  cursor: pointer;
  transition: all 0.18s ease;
  width: 100%;
}

.catalog-item:hover,
.catalog-item.active {
  background: #fff4ee;
  border-color: rgba(198, 111, 79, 0.2);
}

.catalog-item.active .catalog-num {
  color: var(--primary);
}

.catalog-item.active .catalog-title {
  font-weight: 700;
  color: #111827;
}

.catalog-item-main {
  display: flex;
  flex-direction: column;
  gap: 3px;
  text-align: left;
}

.catalog-num {
  font-size: 11px;
  font-weight: 700;
  color: var(--color-text-subtle);
}

.catalog-title {
  font-size: 14px;
  color: var(--color-text);
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.catalog-words {
  font-size: 12px;
  color: var(--text-muted);
}
</style>