<script setup lang="ts">
import ReaderToolbar from '../components/reader/ReaderToolbar.vue'
import ReaderCatalogDrawer from '../components/reader/ReaderCatalogDrawer.vue'
import ReaderContentPane from '../components/reader/ReaderContentPane.vue'
import { useReaderView } from '../composables/useReaderView'

const {
  chapters,
  selectedId,
  chapterLoading,
  chapter,
  catalogSearch,
  drawerVisible,
  settings,
  selectedIndex,
  currentTitle,
  paragraphs,
  readerStyle,
  filteredChapters,
  loadChapters,
  goToWriter,
  goChapter,
  scrollToTop,
  selectChapter,
} = useReaderView()
</script>

<template>
  <div class="reader-container" :class="`theme-${settings.theme}`">
    <ReaderToolbar
      v-model:drawer-visible="drawerVisible"
      :selected-index="selectedIndex"
      :chapter-count="chapters.length"
      :settings="settings"
      @go-chapter="goChapter"
      @scroll-to-top="scrollToTop"
    />

    <ReaderCatalogDrawer
      v-model:drawer-visible="drawerVisible"
      v-model:catalog-search="catalogSearch"
      :chapters="chapters"
      :filtered-chapters="filteredChapters"
      :selected-id="selectedId"
      @select-chapter="selectChapter"
    />

    <ReaderContentPane
      :chapter-loading="chapterLoading"
      :chapter="chapter"
      :paragraphs="paragraphs"
      :selected-id="selectedId"
      :current-title="currentTitle"
      :selected-index="selectedIndex"
      :chapters="chapters"
      :indent="settings.indent"
      :reader-style="readerStyle"
      @go-to-writer="goToWriter"
      @go-chapter="goChapter"
      @reload-chapters="loadChapters"
    />
  </div>
</template>

<style scoped>
.reader-container {
  display: grid;
  grid-template-columns: 1fr;
  min-height: calc(100vh - 64px);
  position: relative;
  margin: -30px -42px -42px;
}

.theme-paper :deep(.reader-content-scroll) {
  background: #f7f1e5;
}

.theme-paper :deep(.novel-content-sheet) {
  background: #fbf6ec;
  color: #2b1f13;
}

.theme-paper :deep(.floating-toolbar),
.theme-paper :deep(.nav-card-btn) {
  background: #fbf6ec;
  border-color: #eadfcc;
}

.theme-paper :deep(.tool-btn) {
  color: #5c4e3e;
}

.theme-paper :deep(.tool-btn:hover) {
  background: #eadfcc;
}

.theme-paper :deep(.bottom-navigator) {
  border-top-color: rgba(43, 31, 19, 0.08);
}

.theme-light :deep(.reader-content-scroll) {
  background: var(--color-bg-surface-muted);
}

.theme-light :deep(.novel-content-sheet) {
  background: var(--color-bg-surface);
  color: var(--color-text-strong);
}

.theme-green :deep(.reader-content-scroll) {
  background: #e3efdf;
}

.theme-green :deep(.novel-content-sheet) {
  background: #edf5eb;
  color: #1a2f1c;
}

.theme-green :deep(.floating-toolbar),
.theme-green :deep(.nav-card-btn) {
  background: #edf5eb;
  border-color: #cddbca;
}

.theme-green :deep(.tool-btn) {
  color: #2b472f;
}

.theme-green :deep(.tool-btn:hover) {
  background: #cddbca;
}

.theme-dark :deep(.reader-content-scroll) {
  background: var(--color-text-strong);
}

.theme-dark :deep(.novel-content-sheet) {
  background: var(--color-text-strong);
  color: var(--color-border);
  border-color: rgba(255, 255, 255, 0.08);
  box-shadow: 0 25px 70px rgba(0, 0, 0, 0.3);
}

.theme-dark :deep(.novel-title-header) {
  border-bottom-color: rgba(255, 255, 255, 0.08);
}

.theme-dark :deep(.novel-title-header h1) {
  color: var(--color-bg-surface-muted);
}

.theme-dark :deep(.floating-toolbar),
.theme-dark :deep(.nav-card-btn) {
  background: var(--color-text-strong);
  border-color: rgba(255, 255, 255, 0.08);
}

.theme-dark :deep(.tool-btn) {
  color: var(--color-text-subtle);
}

.theme-dark :deep(.tool-btn:hover) {
  background: var(--color-text);
  color: #ff9a6d;
}

.theme-dark :deep(.nav-card-btn) {
  color: var(--color-bg-hover);
}

.theme-dark :deep(.nav-card-btn small) {
  color: var(--color-text-subtle);
}

.theme-dark :deep(.bottom-navigator) {
  border-top-color: rgba(255, 255, 255, 0.08);
}
</style>