<script setup lang="ts">
import { ArrowLeft, ArrowRight, Edit } from '@element-plus/icons-vue'
import type { ChapterSummary } from '../../composables/useReaderView'

defineProps<{
  chapterLoading: boolean
  chapter: any
  paragraphs: string[]
  selectedId: string
  currentTitle: string
  selectedIndex: number
  chapters: ChapterSummary[]
  indent: boolean
  readerStyle: Record<string, string | number>
}>()

const emit = defineEmits<{
  goToWriter: []
  goChapter: [offset: number]
  reloadChapters: []
}>()
</script>

<template>
  <div class="reader-content-scroll">
    <main class="reader-main-area" v-loading="chapterLoading">
      <article v-if="chapter && paragraphs.length" class="novel-content-sheet" :style="readerStyle">
        <div class="novel-title-header">
          <div class="chapter-meta-tag">第 {{ selectedId }} 章</div>
          <h1>{{ currentTitle }}</h1>
          <div class="chapter-wordcount-sub">{{ chapter.word_count || 0 }} 汉字 · 沉浸阅读中</div>
          <el-button size="small" type="primary" plain :icon="Edit" @click="emit('goToWriter')">
            去写作页改稿
          </el-button>
        </div>

        <div class="novel-paragraphs-body">
          <p v-for="(paragraph, index) in paragraphs" :key="index" :class="{ indent }">
            {{ paragraph }}
          </p>
        </div>

        <div class="bottom-navigator">
          <button
            class="nav-card-btn prev-card"
            :disabled="selectedIndex <= 0"
            @click="emit('goChapter', -1)"
          >
            <el-icon><ArrowLeft /></el-icon>
            <div>
              <strong>上一章</strong>
              <small v-if="selectedIndex > 0">{{ chapters[selectedIndex - 1].title || '未命名章节' }}</small>
              <small v-else>已经是第一章</small>
            </div>
          </button>

          <button
            class="nav-card-btn next-card"
            :disabled="selectedIndex < 0 || selectedIndex >= chapters.length - 1"
            @click="emit('goChapter', 1)"
          >
            <div>
              <strong>下一章</strong>
              <small v-if="selectedIndex < chapters.length - 1">
                {{ chapters[selectedIndex + 1].title || '未命名章节' }}
              </small>
              <small v-else>已经是最后一章</small>
            </div>
            <el-icon><ArrowRight /></el-icon>
          </button>
        </div>
      </article>

      <div v-else-if="!chapterLoading" class="empty-reader-wrapper">
        <el-empty description="该项目暂无生成的章节正文">
          <el-button type="primary" @click="emit('reloadChapters')">重新加载章节</el-button>
        </el-empty>
      </div>
    </main>
  </div>
</template>

<style scoped>
.reader-content-scroll {
  height: calc(100vh - 64px);
  overflow-y: auto;
  scroll-behavior: smooth;
  padding: 40px 20px 80px;
}

.reader-content-scroll::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.reader-content-scroll::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.3);
  border-radius: 99px;
}

.reader-content-scroll::-webkit-scrollbar-thumb:hover {
  background: rgba(148, 163, 184, 0.5);
}

.reader-main-area {
  min-height: 100%;
  display: flex;
  flex-direction: column;
}

.novel-content-sheet {
  margin: 0 auto;
  padding: 60px 80px;
  border-radius: 12px;
  box-shadow: 0 25px 70px rgba(31, 49, 78, 0.05);
  border: 1px solid rgba(15, 35, 60, 0.05);
}

.novel-title-header {
  text-align: center;
  margin-bottom: 50px;
  padding-bottom: 30px;
  border-bottom: 1px dashed rgba(0, 0, 0, 0.08);
}

.chapter-meta-tag {
  font-size: 13px;
  text-transform: uppercase;
  font-weight: 800;
  letter-spacing: 2px;
  color: var(--primary);
  margin-bottom: 10px;
}

.novel-title-header h1 {
  margin: 0 0 12px;
  font-size: 32px;
  font-weight: 800;
  color: #111827;
  line-height: 1.3;
}

.chapter-wordcount-sub {
  font-size: 13px;
  color: var(--text-muted);
}

.novel-paragraphs-body p {
  margin-top: 0;
  margin-bottom: 1.45em;
  line-height: 1.85;
  color: inherit;
  text-align: justify;
}

.novel-paragraphs-body p.indent {
  text-indent: 2em;
}

.bottom-navigator {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-top: 60px;
  padding-top: 40px;
  border-top: 1px solid rgba(0, 0, 0, 0.06);
}

.nav-card-btn {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 18px 24px;
  border: 1px solid var(--border-light);
  background: white;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #1f2937;
  text-align: left;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.02);
}

.nav-card-btn:hover:not(:disabled) {
  border-color: var(--primary);
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(198, 111, 79, 0.08);
}

.nav-card-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.nav-card-btn.next-card {
  justify-content: space-between;
  text-align: right;
}

.nav-card-btn div {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-card-btn strong {
  font-size: 15px;
  font-weight: 700;
}

.nav-card-btn small {
  font-size: 12px;
  color: var(--text-muted);
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nav-card-btn .el-icon {
  font-size: 20px;
  color: var(--text-muted);
}

.nav-card-btn:hover .el-icon {
  color: var(--primary);
}

.empty-reader-wrapper {
  margin: auto;
}
</style>