<script setup lang="ts">
import { Download, Reading, Refresh, SetUp } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'

import PublicationPreview from '../components/publishing/PublicationPreview.vue'
import PublishingExportPanel from '../components/publishing/PublishingExportPanel.vue'
import PublishingPlatformPanel from '../components/publishing/PublishingPlatformPanel.vue'
import PublishingSummaryStrip from '../components/publishing/PublishingSummaryStrip.vue'
import { usePublishingWorkspace } from '../composables/usePublishingWorkspace'
import ErrorState from '../shared/ui/ErrorState.vue'

const router = useRouter()
const {
  workspace,
  loading,
  chapterLoading,
  saving,
  exporting,
  error,
  activeTab,
  selectedChapterId,
  selectedIndex,
  catalogQuery,
  readerSettings,
  readerStyle,
  filteredChapters,
  paragraphs,
  exportFormat,
  exportScope,
  exportTitle,
  load,
  selectChapter,
  savePlatform,
  saveFeedback,
  download,
} = usePublishingWorkspace()

function openWriter(chapterId: string) {
  void router.push({ path: '/writer', query: { chapter: chapterId } })
}
</script>

<template>
  <section class="publishing-page" v-loading="loading && !workspace">
    <header class="publishing-header">
      <div>
        <small>PUBLICATION WORKSPACE</small>
        <h1>发布中心</h1>
        <p>在一个工作区完成成书预览、平台复核、读者反馈与文件交付。</p>
      </div>
      <div class="header-actions">
        <el-button :icon="Refresh" :loading="loading" @click="load()">刷新</el-button>
        <el-button
          type="primary"
          :icon="Download"
          :disabled="!workspace?.preflight.can_export"
          @click="activeTab = 'export'"
        >
          准备导出
        </el-button>
      </div>
    </header>

    <ErrorState
      v-if="error && !workspace"
      title="发布中心加载失败"
      :description="error"
      action-label="重试"
      @action="load()"
    />

    <template v-else-if="workspace">
      <PublishingSummaryStrip :workspace="workspace" />

      <nav class="publishing-tabs" aria-label="发布中心分区">
        <button
          type="button"
          :class="{ active: activeTab === 'preview' }"
          @click="activeTab = 'preview'"
        >
          <el-icon><Reading /></el-icon>
          成书预览
          <span>{{ workspace.book.chapter_count }}</span>
        </button>
        <button
          type="button"
          :class="{ active: activeTab === 'platform' }"
          @click="activeTab = 'platform'"
        >
          <el-icon><SetUp /></el-icon>
          平台与反馈
          <span>{{ workspace.golden_check.ready_count }}/3</span>
        </button>
        <button
          type="button"
          :class="{ active: activeTab === 'export' }"
          @click="activeTab = 'export'"
        >
          <el-icon><Download /></el-icon>
          导出交付
          <span :class="{ danger: workspace.preflight.blocking_count }">
            {{ workspace.preflight.blocking_count || workspace.preflight.warning_count || '✓' }}
          </span>
        </button>
      </nav>

      <main class="publishing-canvas">
        <PublicationPreview
          v-if="activeTab === 'preview'"
          v-model:catalog-query="catalogQuery"
          v-model:settings="readerSettings"
          :chapters="workspace.chapters.filter((item) => item.has_content)"
          :filtered-chapters="filteredChapters"
          :selected-chapter="workspace.selected_chapter"
          :selected-chapter-id="selectedChapterId"
          :selected-index="selectedIndex"
          :paragraphs="paragraphs"
          :chapter-loading="chapterLoading"
          :reader-style="readerStyle"
          @select="selectChapter"
          @edit="openWriter"
        />
        <PublishingPlatformPanel
          v-else-if="activeTab === 'platform'"
          :workspace="workspace"
          :selected-chapter-id="selectedChapterId"
          :saving="saving"
          @platform="savePlatform"
          @feedback="saveFeedback"
        />
        <PublishingExportPanel
          v-else
          v-model:format="exportFormat"
          v-model:scope="exportScope"
          v-model:title="exportTitle"
          :workspace="workspace"
          :selected-chapter-id="selectedChapterId"
          :exporting="exporting"
          @download="download"
          @navigate="router.push($event)"
        />
      </main>
    </template>
  </section>
</template>

<style scoped>
.publishing-page {
  display: flex;
  height: 100%;
  min-height: 0;
  flex-direction: column;
  gap: 9px;
  overflow: hidden;
  padding: 14px 16px 16px;
  background: var(--color-bg-page);
}
.publishing-header { display: flex; flex-shrink: 0; align-items: center; justify-content: space-between; gap: 18px; }
.publishing-header > div:first-child { display: grid; gap: 3px; }
.publishing-header small { color: var(--color-primary); font-size: 9px; font-weight: 800; letter-spacing: .12em; }
.publishing-header h1 { margin: 0; color: var(--color-text-strong); font-size: 22px; line-height: 1.1; }
.publishing-header p { margin: 0; color: var(--color-text-muted); font-size: 11px; }
.header-actions { display: flex; gap: 8px; }
.publishing-tabs {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 3px;
  min-height: 38px;
  padding: 3px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  background: var(--color-bg-surface);
}
.publishing-tabs button {
  display: inline-flex;
  min-height: 30px;
  align-items: center;
  gap: 7px;
  padding: 0 13px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--color-text-muted);
  cursor: pointer;
  font-size: 11px;
  font-weight: 700;
}
.publishing-tabs button:hover { color: var(--color-text-strong); background: var(--color-bg-hover); }
.publishing-tabs button.active { color: var(--color-primary); background: var(--color-primary-soft); }
.publishing-tabs button > span {
  min-width: 17px;
  padding: 2px 5px;
  border-radius: 999px;
  background: var(--color-bg-surface-muted);
  color: var(--color-text-muted);
  font-size: 8px;
  text-align: center;
}
.publishing-tabs button > span.danger { background: var(--color-danger-soft); color: var(--color-danger); }
.publishing-canvas {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-surface);
  box-shadow: var(--shadow-sm);
}
@media (max-width: 900px) {
  .publishing-page { padding: 10px; }
  .publishing-header p { display: none; }
}
</style>
