<script setup lang="ts">
import { Fold, Document, Plus, Delete } from '@element-plus/icons-vue'
import { useTasksStore } from '../../stores/tasks'

defineProps<{
  chaptersList: any[]
  activeChapterId: string
  onLoadChapter: (chapterId: string) => void
  onOpenCreateChapter: () => void
  onDeleteChapter: (chapterId: string) => void
}>()

const collapsed = defineModel<boolean>('collapsed', { required: true })

const tasksStore = useTasksStore()
</script>

<template>
  <div class="chapter-sidebar" :class="{ collapsed }">
    <div class="sidebar-header">
      <span class="sidebar-title">📖 章节目录</span>
      <div style="display: flex; align-items: center; gap: 6px;">
        <el-button
          type="primary"
          size="small"
          circle
          :icon="Plus"
          :disabled="tasksStore.isRunning"
          @click="onOpenCreateChapter"
          title="新建章节"
        />
        <el-button
          type="text"
          :icon="Fold"
          class="collapse-btn"
          @click="collapsed = true"
          title="收起目录"
          style="margin: 0; padding: 4px;"
        />
      </div>
    </div>
    <div class="chapter-list-scroll">
      <div
        v-for="ch in chaptersList"
        :key="ch.chapter_id"
        class="chapter-item"
        :class="{ active: activeChapterId === ch.chapter_id }"
        @click="onLoadChapter(ch.chapter_id)"
      >
        <div class="chapter-item-header">
          <el-icon class="chapter-icon"><Document /></el-icon>
          <span class="chapter-item-title">{{ ch.chapter_id }}. {{ ch.title || '未命名章节' }}</span>
          <el-button
            class="chapter-delete-btn"
            type="danger"
            link
            :icon="Delete"
            title="删除章节"
            :disabled="tasksStore.isRunning"
            @click.stop="onDeleteChapter(ch.chapter_id)"
          />
        </div>
        <span v-if="ch.word_count" class="chapter-item-wc">{{ ch.word_count }}字</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chapter-list-scroll::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
.chapter-list-scroll::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.3);
  border-radius: 99px;
}
.chapter-list-scroll::-webkit-scrollbar-thumb:hover {
  background: rgba(148, 163, 184, 0.5);
}

.chapter-sidebar {
  width: 240px;
  height: 100%;
  border-right: 1px solid var(--color-border);
  background: var(--color-bg-surface-muted);
  display: flex;
  flex-direction: column;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1), min-width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  flex-shrink: 0;
}
.chapter-sidebar.collapsed {
  width: 0;
  min-width: 0;
  border-right: none;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px;
  border-bottom: 1px solid var(--color-border-subtle);
  background: var(--color-bg-surface-muted);
  flex-shrink: 0;
}
.sidebar-title {
  font-size: 14px;
  font-weight: 800;
  color: var(--color-text);
  letter-spacing: 0.05em;
}
.collapse-btn {
  color: var(--color-text-muted);
  padding: 4px;
  border-radius: 6px;
  transition: all 0.2s;
}
.collapse-btn:hover {
  background: var(--color-border);
  color: var(--color-text-strong);
}

.chapter-list-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chapter-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 14px;
  border-radius: 8px;
  cursor: pointer;
  background: transparent;
  border: 1px solid transparent;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  user-select: none;
  position: relative;
}
.chapter-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 15%;
  height: 70%;
  width: 3px;
  background: transparent;
  border-radius: 0 4px 4px 0;
  transition: all 0.2s;
}
.chapter-item:hover {
  background: var(--color-bg-hover);
}
.chapter-item.active {
  background: var(--color-bg-surface);
  border-color: var(--color-border);
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03);
}
.chapter-item.active::before {
  background: var(--primary, #c66f4f);
}

.chapter-item-header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.chapter-icon {
  font-size: 13px;
  color: var(--color-text-subtle);
  transition: color 0.2s;
}
.chapter-item.active .chapter-icon {
  color: var(--primary, #c66f4f);
}

.chapter-item-title {
  font-size: 13.5px;
  font-weight: 600;
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color 0.2s;
}
.chapter-delete-btn {
  margin-left: auto;
  opacity: 0;
  transition: opacity 0.2s ease;
}
.chapter-item:hover .chapter-delete-btn,
.chapter-item.active .chapter-delete-btn {
  opacity: 1;
}
.chapter-item.active .chapter-item-title {
  color: var(--color-text-strong);
}

.chapter-item-wc {
  align-self: flex-start;
  font-size: 10.5px;
  background: var(--color-border);
  color: var(--color-text-muted);
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
  margin-left: 21px;
}
</style>