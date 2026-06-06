<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, ArrowRight, Menu, Setting, CaretTop, Search, Edit } from '@element-plus/icons-vue'
import { getChapter, listChapters } from '../api'

const router = useRouter()

interface ChapterSummary {
  chapter_id: string
  title: string
  word_count: number
}

interface ReaderSettings {
  fontSize: number
  lineHeight: number
  width: number
  indent: boolean
  theme: 'paper' | 'light' | 'dark' | 'green'
}

const SETTINGS_KEY = 'novel-agent-reader-settings'

const chapters = ref<ChapterSummary[]>([])
const selectedId = ref('')
const loading = ref(false)
const chapterLoading = ref(false)
const chapter = ref<any>(null)
const catalogSearch = ref('')
const drawerVisible = ref(false)

const settings = ref<ReaderSettings>({
  fontSize: 20,
  lineHeight: 1.8,
  width: 800,
  indent: true,
  theme: 'paper',
})

const selectedIndex = computed(() => chapters.value.findIndex((item) => item.chapter_id === selectedId.value))
const currentTitle = computed(() => chapter.value?.title || chapters.value[selectedIndex.value]?.title || '未命名章节')
const paragraphs = computed(() => {
  const text = chapter.value?.final_text || ''
  return text
    .split(/\n+/)
    .map((part: string) => part.trim())
    .filter(Boolean)
})
const readerStyle = computed(() => ({
  maxWidth: `${settings.value.width}px`,
  fontSize: `${settings.value.fontSize}px`,
  lineHeight: settings.value.lineHeight,
}))

// Filtered chapters for the catalog drawer
const filteredChapters = computed(() => {
  if (!catalogSearch.value.trim()) return chapters.value
  const query = catalogSearch.value.toLowerCase()
  return chapters.value.filter(
    (c) =>
      c.chapter_id.includes(query) ||
      (c.title || '').toLowerCase().includes(query)
  )
})

const loadSettings = () => {
  try {
    const saved = JSON.parse(localStorage.getItem(SETTINGS_KEY) || '{}')
    settings.value = { ...settings.value, ...saved }
  } catch {
    localStorage.removeItem(SETTINGS_KEY)
  }
}

const loadChapters = async () => {
  loading.value = true
  try {
    const { data } = await listChapters({ offset: 0, limit: 500, sync: true })
    chapters.value = data.items ?? data
    if (!selectedId.value && chapters.value.length) {
      selectedId.value = chapters.value[0].chapter_id
    }
  } finally {
    loading.value = false
  }
}

const goToWriter = () => {
  if (!selectedId.value) return
  router.push({ path: '/writer', query: { chapter: selectedId.value } })
}

const loadChapter = async (chapterId: string) => {
  if (!chapterId) {
    chapter.value = null
    return
  }
  chapterLoading.value = true
  try {
    const { data } = await getChapter(chapterId)
    chapter.value = data
    scrollToTop()
  } finally {
    chapterLoading.value = false
  }
}

const goChapter = (offset: number) => {
  const next = chapters.value[selectedIndex.value + offset]
  if (next) {
    selectedId.value = next.chapter_id
  }
}

const scrollToTop = () => {
  const mainEl = document.querySelector('.reader-content-scroll')
  if (mainEl) {
    mainEl.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

watch(selectedId, (id) => loadChapter(id), { immediate: false })
watch(settings, (value) => localStorage.setItem(SETTINGS_KEY, JSON.stringify(value)), { deep: true })

onMounted(async () => {
  loadSettings()
  await loadChapters()
})
</script>

<template>
  <div class="reader-container" :class="`theme-${settings.theme}`">
    <!-- Floating Vertical ToolBar -->
    <div class="floating-toolbar">
      <el-tooltip content="目录 (Catalog)" placement="right">
        <button class="tool-btn" @click="drawerVisible = true">
          <el-icon><Menu /></el-icon>
        </button>
      </el-tooltip>

      <el-popover placement="right" trigger="click" width="300" popper-class="reader-settings-popover">
        <template #reference>
          <button class="tool-btn">
            <el-icon><Setting /></el-icon>
          </button>
        </template>
        
        <div class="settings-panel">
          <h3>阅读器设置</h3>
          
          <div class="settings-item">
            <span>配色主题</span>
            <el-segmented
              v-model="settings.theme"
              :options="[
                { label: '宣纸', value: 'paper' },
                { label: '雅白', value: 'light' },
                { label: '护眼', value: 'green' },
                { label: '夜间', value: 'dark' },
              ]"
              size="small"
            />
          </div>

          <div class="settings-item">
            <span>系统字号 (px)</span>
            <el-input-number v-model="settings.fontSize" :min="14" :max="32" :step="1" size="small" controls-position="right" />
          </div>

          <div class="settings-item">
            <span>文字行高</span>
            <el-input-number v-model="settings.lineHeight" :min="1.4" :max="2.5" :step="0.1" :precision="1" size="small" controls-position="right" />
          </div>

          <div class="settings-item">
            <span>阅读宽度 (px)</span>
            <el-slider v-model="settings.width" :min="600" :max="1000" :step="40" style="flex: 1; margin-left: 10px;" />
          </div>

          <div class="settings-item">
            <span>首行缩进</span>
            <el-switch v-model="settings.indent" active-color="#c66f4f" />
          </div>
        </div>
      </el-popover>

      <div class="divider"></div>

      <el-tooltip content="上一章" placement="right">
        <button class="tool-btn" :disabled="selectedIndex <= 0" @click="goChapter(-1)">
          <el-icon><ArrowLeft /></el-icon>
        </button>
      </el-tooltip>

      <el-tooltip content="下一章" placement="right">
        <button class="tool-btn" :disabled="selectedIndex < 0 || selectedIndex >= chapters.length - 1" @click="goChapter(1)">
          <el-icon><ArrowRight /></el-icon>
        </button>
      </el-tooltip>

      <el-tooltip content="回到顶部" placement="right">
        <button class="tool-btn" @click="scrollToTop">
          <el-icon><CaretTop /></el-icon>
        </button>
      </el-tooltip>
    </div>

    <!-- Chapter Catalog Drawer -->
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
              @click="selectedId = item.chapter_id; drawerVisible = false"
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

    <!-- Main Content Reader Area -->
    <div class="reader-content-scroll">
      <main class="reader-main-area" v-loading="chapterLoading">
        <article v-if="chapter && paragraphs.length" class="novel-content-sheet" :style="readerStyle">
          <div class="novel-title-header">
            <div class="chapter-meta-tag">第 {{ selectedId }} 章</div>
            <h1>{{ currentTitle }}</h1>
            <div class="chapter-wordcount-sub">{{ chapter.word_count || 0 }} 汉字 · 沉浸阅读中</div>
            <el-button size="small" type="primary" plain :icon="Edit" @click="goToWriter">
              去写作页改稿
            </el-button>
          </div>

          <div class="novel-paragraphs-body">
            <p v-for="(paragraph, index) in paragraphs" :key="index" :class="{ indent: settings.indent }">
              {{ paragraph }}
            </p>
          </div>

          <!-- Bottom page navigation cards -->
          <div class="bottom-navigator">
            <button
              class="nav-card-btn prev-card"
              :disabled="selectedIndex <= 0"
              @click="goChapter(-1)"
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
              @click="goChapter(1)"
            >
              <div>
                <strong>下一章</strong>
                <small v-if="selectedIndex < chapters.length - 1">{{ chapters[selectedIndex + 1].title || '未命名章节' }}</small>
                <small v-else>已经是最后一章</small>
              </div>
              <el-icon><ArrowRight /></el-icon>
            </button>
          </div>
        </article>

        <div v-else-if="!chapterLoading" class="empty-reader-wrapper">
          <el-empty description="该项目暂无生成的章节正文">
            <el-button type="primary" @click="loadChapters">重新加载章节</el-button>
          </el-empty>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.reader-container {
  display: grid;
  grid-template-columns: 1fr;
  min-height: calc(100vh - 64px);
  position: relative;
  margin: -30px -42px -42px; /* Pull to full workspace */
}

/* Floating Vertical Tool Panel */
.floating-toolbar {
  position: fixed;
  left: 310px; /* Aligned next to workspace sidebar */
  top: 120px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 10px;
  background: white;
  border: 1px solid var(--border-light);
  border-radius: 99px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
  z-index: 100;
}

.tool-btn {
  width: 42px;
  height: 42px;
  border-radius: 99px;
  border: none;
  background: transparent;
  color: #4b5563;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 18px;
}

.tool-btn:hover:not(:disabled) {
  background: var(--color-bg-hover);
  color: var(--primary);
  transform: scale(1.05);
}

.tool-btn:disabled {
  color: #d1d5db;
  cursor: not-allowed;
}

.floating-toolbar .divider {
  height: 1px;
  background: var(--color-border);
  margin: 4px 6px;
}

/* Reader Main Content Scroller */
.reader-content-scroll {
  height: calc(100vh - 64px);
  overflow-y: auto;
  scroll-behavior: smooth;
  padding: 40px 20px 80px;
}

.reader-main-area {
  min-height: 100%;
  display: flex;
  flex-direction: column;
}

/* Novel sheet representation */
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

/* Bottom Nav Cards */
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

/* Color Themes Styles */
/* 1. Paper / Sepia Theme */
.theme-paper .reader-content-scroll {
  background: #f7f1e5;
}
.theme-paper .novel-content-sheet {
  background: #fbf6ec;
  color: #2b1f13;
}
.theme-paper .floating-toolbar,
.theme-paper .nav-card-btn {
  background: #fbf6ec;
  border-color: #eadfcc;
}
.theme-paper .tool-btn {
  color: #5c4e3e;
}
.theme-paper .tool-btn:hover {
  background: #eadfcc;
}
.theme-paper .bottom-navigator {
  border-top-color: rgba(43, 31, 19, 0.08);
}

/* 2. Light Theme */
.theme-light .reader-content-scroll {
  background: var(--color-bg-surface-muted);
}
.theme-light .novel-content-sheet {
  background: var(--color-bg-surface);
  color: var(--color-text-strong);
}

/* 3. Green / Eye Protection Theme */
.theme-green .reader-content-scroll {
  background: #e3efdf;
}
.theme-green .novel-content-sheet {
  background: #edf5eb;
  color: #1a2f1c;
}
.theme-green .floating-toolbar,
.theme-green .nav-card-btn {
  background: #edf5eb;
  border-color: #cddbca;
}
.theme-green .tool-btn {
  color: #2b472f;
}
.theme-green .tool-btn:hover {
  background: #cddbca;
}

/* 4. Night / Dark Theme */
.theme-dark .reader-content-scroll {
  background: var(--color-text-strong);
}
.theme-dark .novel-content-sheet {
  background: var(--color-text-strong);
  color: var(--color-border);
  border-color: rgba(255, 255, 255, 0.08);
  box-shadow: 0 25px 70px rgba(0, 0, 0, 0.3);
}
.theme-dark .novel-title-header {
  border-bottom-color: rgba(255, 255, 255, 0.08);
}
.theme-dark .novel-title-header h1 {
  color: var(--color-bg-surface-muted);
}
.theme-dark .floating-toolbar,
.theme-dark .nav-card-btn {
  background: var(--color-text-strong);
  border-color: rgba(255, 255, 255, 0.08);
}
.theme-dark .tool-btn {
  color: var(--color-text-subtle);
}
.theme-dark .tool-btn:hover {
  background: var(--color-text);
  color: #ff9a6d;
}
.theme-dark .nav-card-btn {
  color: var(--color-bg-hover);
}
.theme-dark .nav-card-btn small {
  color: var(--color-text-subtle);
}
.theme-dark .bottom-navigator {
  border-top-color: rgba(255, 255, 255, 0.08);
}

/* Catalog Drawer custom styling */
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

/* Popover details settings */
.settings-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 6px;
}

.settings-panel h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 800;
  color: var(--color-text-strong);
  border-bottom: 1px solid var(--color-bg-hover);
  padding-bottom: 8px;
}

.settings-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13.5px;
  color: var(--color-text-muted);
}

.empty-reader-wrapper {
  margin: auto;
}

@media (max-width: 1200px) {
  .floating-toolbar {
    left: 20px;
    top: auto;
    bottom: 40px;
    flex-direction: row;
    border-radius: 99px;
    padding: 6px 14px;
  }
  
  .floating-toolbar .divider {
    width: 1px;
    height: 24px;
    margin: 6px 4px;
  }
}

/* Custom Scrollbars */
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
</style>
