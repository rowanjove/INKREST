<script setup lang="ts">
import { ArrowLeft, ArrowRight, Edit, Search } from '@element-plus/icons-vue'

import type {
  PublicationChapter,
  PublicationChapterSummary,
  ReaderSettings,
} from '../../entities/publishing/publishing'

const props = defineProps<{
  chapters: PublicationChapterSummary[]
  filteredChapters: PublicationChapterSummary[]
  selectedChapter: PublicationChapter | null
  selectedChapterId: string
  selectedIndex: number
  paragraphs: string[]
  chapterLoading: boolean
  readerStyle: Record<string, string>
}>()
const catalogQuery = defineModel<string>('catalogQuery', { required: true })
const settings = defineModel<ReaderSettings>('settings', { required: true })
const emit = defineEmits<{
  select: [chapterId: string]
  edit: [chapterId: string]
}>()

function move(offset: number) {
  const target = props.chapters[props.selectedIndex + offset]
  if (target?.has_content) emit('select', target.chapter_id)
}
</script>

<template>
  <section class="preview-workspace">
    <aside class="catalog-panel">
      <header>
        <div><strong>成书目录</strong><span>{{ chapters.filter((item) => item.has_content).length }} 章</span></div>
        <el-input
          v-model="catalogQuery"
          :prefix-icon="Search"
          placeholder="搜索章节"
          clearable
          size="small"
        />
      </header>
      <div class="catalog-list">
        <button
          v-for="chapter in filteredChapters"
          :key="chapter.chapter_id"
          type="button"
          :class="{ active: chapter.chapter_id === selectedChapterId }"
          @click="emit('select', chapter.chapter_id)"
        >
          <span>第 {{ Number(chapter.chapter_id) || chapter.chapter_id }} 章</span>
          <strong>{{ chapter.title || '未命名章节' }}</strong>
          <small>{{ chapter.word_count.toLocaleString('zh-CN') }} 字 · R{{ chapter.revision }}</small>
        </button>
        <div v-if="!filteredChapters.length" class="catalog-empty">没有匹配的正文章节</div>
      </div>
    </aside>

    <section class="reader-panel">
      <header class="reader-controls">
        <div class="reader-controls-copy">
          <strong>阅读版式</strong>
          <span>仅影响预览，不修改正文</span>
        </div>
        <label>
          字号
          <el-slider v-model="settings.fontSize" :min="14" :max="26" :step="1" />
        </label>
        <label>
          行距
          <el-input-number
            v-model="settings.lineHeight"
            :min="1.4"
            :max="2.4"
            :step="0.1"
            :precision="1"
            size="small"
            controls-position="right"
          />
        </label>
        <label>
          版心
          <el-select v-model="settings.width" size="small">
            <el-option :value="680" label="紧凑" />
            <el-option :value="760" label="标准" />
            <el-option :value="860" label="宽松" />
          </el-select>
        </label>
        <el-switch v-model="settings.indent" inline-prompt active-text="缩进" inactive-text="顶格" />
      </header>

      <div class="publication-reader-scroll" v-loading="chapterLoading">
        <article v-if="selectedChapter" class="book-sheet" :style="readerStyle">
          <header>
            <small>CHAPTER {{ selectedChapter.chapter_id }}</small>
            <h1>{{ selectedChapter.title || '未命名章节' }}</h1>
            <p>
              {{ selectedChapter.word_count.toLocaleString('zh-CN') }} 字
              <span>·</span>
              文稿修订 R{{ selectedChapter.revision }}
            </p>
            <el-button
              size="small"
              plain
              :icon="Edit"
              @click="emit('edit', selectedChapter.chapter_id)"
            >
              返回正文修改
            </el-button>
          </header>
          <div class="book-body">
            <p v-for="(paragraph, index) in paragraphs" :key="index" :class="{ indent: settings.indent }">
              {{ paragraph }}
            </p>
          </div>
          <footer>
            <button type="button" :disabled="selectedIndex <= 0" @click="move(-1)">
              <el-icon><ArrowLeft /></el-icon><span>上一章</span>
            </button>
            <button
              type="button"
              :disabled="selectedIndex < 0 || selectedIndex >= chapters.length - 1"
              @click="move(1)"
            >
              <span>下一章</span><el-icon><ArrowRight /></el-icon>
            </button>
          </footer>
        </article>
        <el-empty v-else description="还没有可预览的已保存正文" />
      </div>
    </section>
  </section>
</template>

<style scoped>
.preview-workspace {
  display: grid;
  height: 100%;
  min-height: 0;
  grid-template-columns: 232px minmax(0, 1fr);
}
.catalog-panel {
  display: grid;
  min-height: 0;
  grid-template-rows: auto minmax(0, 1fr);
  border-right: 1px solid var(--color-border);
  background: var(--color-bg-surface-muted);
}
.catalog-panel > header { display: grid; gap: 10px; padding: 14px; border-bottom: 1px solid var(--color-border); }
.catalog-panel > header > div { display: flex; align-items: center; justify-content: space-between; }
.catalog-panel strong { color: var(--color-text-strong); font-size: 12px; }
.catalog-panel header span { color: var(--color-text-muted); font-size: 10px; }
.catalog-list { min-height: 0; overflow: auto; padding: 8px; }
.catalog-list button {
  display: grid;
  width: 100%;
  gap: 3px;
  padding: 10px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  text-align: left;
}
.catalog-list button:hover { background: var(--color-bg-hover); }
.catalog-list button.active {
  border-color: color-mix(in srgb, var(--color-primary) 32%, transparent);
  background: var(--color-primary-soft);
}
.catalog-list button > span { color: var(--color-primary); font-size: 9px; font-weight: 800; letter-spacing: .04em; }
.catalog-list button strong { overflow: hidden; font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.catalog-list button small { color: var(--color-text-subtle); font-size: 9px; }
.catalog-empty { padding: 30px 12px; color: var(--color-text-muted); font-size: 11px; text-align: center; }
.reader-panel { display: grid; min-width: 0; min-height: 0; grid-template-rows: auto minmax(0, 1fr); }
.reader-controls {
  display: flex;
  min-height: 54px;
  align-items: center;
  gap: 16px;
  padding: 8px 14px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-surface);
}
.reader-controls-copy { display: grid; min-width: 130px; margin-right: auto; gap: 1px; }
.reader-controls strong { color: var(--color-text-strong); font-size: 11px; }
.reader-controls span { color: var(--color-text-muted); font-size: 9px; }
.reader-controls label { display: flex; align-items: center; gap: 7px; color: var(--color-text-muted); font-size: 9px; white-space: nowrap; }
.reader-controls label .el-slider { width: 72px; }
.reader-controls label .el-select { width: 84px; }
.publication-reader-scroll {
  min-height: 0;
  overflow: auto;
  padding: 24px 20px 60px;
  background: color-mix(in srgb, var(--color-bg-surface-muted) 88%, #ead9c2);
}
.book-sheet {
  box-sizing: border-box;
  width: min(100%, 860px);
  min-height: calc(100% - 20px);
  margin: 0 auto;
  padding: clamp(36px, 6vw, 72px) clamp(32px, 8vw, 86px);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background: var(--color-bg-surface);
  color: var(--color-text);
  box-shadow: var(--shadow-panel);
  font-family: var(--font-serif), 'Songti SC', serif;
}
.book-sheet > header { margin-bottom: 38px; padding-bottom: 26px; border-bottom: 1px solid var(--color-border-subtle); text-align: center; }
.book-sheet > header small { color: var(--color-primary); font-family: var(--font-sans); font-size: 9px; font-weight: 800; letter-spacing: .12em; }
.book-sheet h1 { margin: 10px 0 8px; color: var(--color-text-strong); font-size: 26px; line-height: 1.3; }
.book-sheet > header p { margin: 0 0 14px; color: var(--color-text-muted); font-family: var(--font-sans); font-size: 10px; }
.book-sheet > header p span { margin: 0 5px; }
.book-body p { margin: 0 0 1.35em; color: inherit; text-align: justify; }
.book-body p.indent { text-indent: 2em; }
.book-sheet footer {
  display: flex;
  justify-content: space-between;
  margin-top: 44px;
  padding-top: 20px;
  border-top: 1px solid var(--color-border-subtle);
}
.book-sheet footer button {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 8px 10px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
}
.book-sheet footer button:hover:not(:disabled) { background: var(--color-primary-soft); color: var(--color-primary); }
.book-sheet footer button:disabled { opacity: .35; cursor: not-allowed; }
@media (max-width: 1200px) {
  .reader-controls-copy { display: none; }
  .reader-controls { justify-content: flex-end; gap: 12px; }
}
@media (max-width: 880px) {
  .preview-workspace { grid-template-columns: 190px minmax(0, 1fr); }
  .reader-controls label:first-of-type { display: none; }
  .book-sheet { padding-inline: 36px; }
}
</style>
