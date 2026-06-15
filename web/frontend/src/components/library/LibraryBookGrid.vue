<script setup lang="ts">
import { Delete, Download, Reading } from '@element-plus/icons-vue'
import type { Project } from '../../stores/project'
import {
  formatWords,
  getCoverClass,
  lastEditLabel,
  lastEditTime,
  lastEditTitle,
} from '../../utils/libraryFormatters'

defineProps<{
  projects: Project[]
  pinningId: string | null
  getCoverStyle: (project: Project) => Record<string, string | undefined>
  onOpenProject: (id: string) => void
  onTogglePin: (project: Project, event: Event) => void
  onOpenPendingMaintenance: (project: Project, event: Event) => void
  onOpenDetails: (project: Project) => void
  onHandleRead: (id: string) => void
  onHandleDelete: (id: string, name: string) => void
  onHandleExportFormat: (format: string, project: Project) => void
}>()
</script>

<template>
  <div class="project-grid">
    <article
      v-for="project in projects"
      :key="project.id"
      class="project-card"
      :class="{ 'is-pinned': project.pinned }"
      @click="onOpenProject(project.id)"
    >
      <div class="book-spine" aria-hidden="true" />
      <div class="book-spine-shadow" aria-hidden="true" />
      <div
        class="book-cover"
        :class="[getCoverClass(project.channel), { 'has-cover': project.has_cover }]"
        :style="getCoverStyle(project)"
      >
        <button
          type="button"
          class="pin-btn"
          :class="{ active: project.pinned }"
          :title="project.pinned ? '取消置顶' : '置顶（最多 10 本）'"
          :disabled="pinningId === project.id"
          @click="onTogglePin(project, $event)"
        >
          <span class="pin-glyph" aria-hidden="true" />
        </button>
        <div class="cover-design">
          <span v-if="project.genre" class="genre-badge">{{ project.genre }}</span>
          <button
            v-if="(project.pending_alert_count || 0) > 0"
            type="button"
            class="pending-badge"
            :title="`有 ${project.pending_alert_count} 章待处理，点击直达修章维护`"
            @click="onOpenPendingMaintenance(project, $event)"
          >
            待处理 {{ project.pending_alert_count }} 章
          </button>
          <h2 class="book-title" @click.stop="onOpenDetails(project)">{{ project.name }}</h2>
          <p v-if="project.author_label" class="book-author-label">{{ project.author_label }}</p>
        </div>

        <div class="cover-footer">
          <div class="book-meta">
            <p class="meta-inline-stats">
              <span class="meta-inline-item">{{ project.chapter_count || 0 }} 章</span>
              <span class="meta-sep" aria-hidden="true">·</span>
              <span class="meta-inline-item">{{ formatWords(project.total_words) }}</span>
            </p>
            <p class="meta-updated" :title="lastEditTitle(project)">
              更新 {{ lastEditLabel(project) }}
            </p>
          </div>

          <div class="cover-footer-bottom" @click.stop>
            <span v-if="lastEditTime(project)" class="meta-time">{{ lastEditTime(project) }}</span>
            <span v-else class="meta-time meta-time--empty">--:--</span>
            <div class="book-actions">
              <el-button
                class="action-btn read-btn"
                text
                size="small"
                :icon="Reading"
                @click="onHandleRead(project.id)"
              />
              <el-dropdown
                trigger="click"
                @command="(fmt: string) => onHandleExportFormat(fmt, project)"
              >
                <el-button
                  class="action-btn export-btn"
                  text
                  size="small"
                  :icon="Download"
                />
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="markdown">导出为 Markdown (.md)</el-dropdown-item>
                    <el-dropdown-item command="docx">导出为 Word (.docx)</el-dropdown-item>
                    <el-dropdown-item command="txt">导出为 文本 (.txt)</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
              <el-button
                class="action-btn delete-btn"
                text
                size="small"
                :icon="Delete"
                @click="onHandleDelete(project.id, project.name)"
              />
            </div>
          </div>
        </div>
      </div>
    </article>
  </div>
</template>

<style scoped>
.project-card.is-pinned {
  outline: 2px solid rgba(198, 111, 79, 0.45);
  outline-offset: 2px;
}

.pin-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 4;
  width: 30px;
  height: 30px;
  padding: 0;
  border: 1px solid rgba(255, 255, 255, 0.55);
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.42);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s, transform 0.15s;
  backdrop-filter: blur(4px);
}

.pin-btn:hover {
  background: rgba(15, 23, 42, 0.62);
  transform: scale(1.05);
}

.pin-btn.active {
  background: rgba(198, 111, 79, 0.92);
  border-color: rgba(255, 255, 255, 0.7);
}

.pin-glyph {
  display: block;
  width: 11px;
  height: 11px;
  background: var(--color-bg-surface);
  border-radius: 50% 50% 50% 0;
  transform: rotate(-45deg);
  box-shadow: inset 0 -2px 0 rgba(0, 0, 0, 0.12);
}

.pin-btn.active .pin-glyph {
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.35);
}

.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, 210px);
  grid-auto-rows: 288px;
  justify-content: start;
  gap: 0 30px;
  min-height: 360px;
  position: relative;
  z-index: 10;
  background: repeating-linear-gradient(
    to bottom,
    transparent 0px,
    transparent 220px,
    rgba(201, 159, 104, 0.22) 220px 223px,
    #ead6b5 223px 232px,
    #d3ad78 232px 243px,
    #b9864d 243px 248px,
    rgba(118, 81, 43, 0.16) 248px 260px,
    transparent 260px 288px
  );
}

.project-card {
  position: relative;
  width: 190px;
  height: 224px;
  justify-self: center;
  background: transparent;
  border: none;
  cursor: pointer;
  perspective: 1000px;
  transform-style: preserve-3d;
  transition: transform 0.4s ease;
  user-select: none;
}

.book-spine {
  position: absolute;
  top: 0;
  left: 0;
  width: 14px;
  height: 100%;
  background: linear-gradient(
    to right,
    rgba(0, 0, 0, 0.18) 0%,
    rgba(0, 0, 0, 0.04) 28%,
    rgba(255, 255, 255, 0.14) 44%,
    rgba(255, 255, 255, 0) 50%,
    rgba(0, 0, 0, 0.1) 100%
  );
  border-radius: 4px 0 0 4px;
  z-index: 10;
  pointer-events: none;
}

.book-spine-shadow {
  position: absolute;
  top: 0;
  left: 14px;
  width: 6px;
  height: 100%;
  background: linear-gradient(to right, rgba(0, 0, 0, 0.12), rgba(0, 0, 0, 0));
  z-index: 6;
  pointer-events: none;
}

.book-cover {
  position: absolute;
  top: 0;
  left: 0;
  width: calc(100% - 14px);
  height: 100%;
  border: 1px solid rgba(255, 255, 255, 0.46);
  border-radius: 6px 2px 2px 6px;
  background:
    linear-gradient(to bottom, rgba(255, 255, 255, 0.16), rgba(255, 255, 255, 0) 36%),
    radial-gradient(circle at 78% 18%, rgba(255, 255, 255, 0.22), transparent 18%),
    linear-gradient(135deg, var(--cover-start), var(--cover-mid) 52%, var(--cover-end));
  box-shadow:
    2px 6px 12px rgba(60, 42, 24, 0.2),
    inset 14px 0 18px rgba(0, 0, 0, 0.12),
    inset -1px 0 0 rgba(255, 255, 255, 0.28);
  transform-origin: left center;
  transition: transform 0.4s cubic-bezier(0.25, 0.8, 0.25, 1), box-shadow 0.4s ease;
  z-index: 5;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 14px;
  color: var(--color-bg-surface);
  overflow: hidden;
}

.cover-general {
  --cover-start: #3f7f75;
  --cover-mid: #73a88b;
  --cover-end: #d7be84;
}

.cover-male {
  --cover-start: #425f83;
  --cover-mid: #6f89ad;
  --cover-end: #d5c095;
}

.cover-female {
  --cover-start: #b86978;
  --cover-mid: #d89483;
  --cover-end: #ead19a;
}

.cover-custom {
  --cover-start: #76648d;
  --cover-mid: #9f8dae;
  --cover-end: #dcc28d;
}

.project-card:hover .book-cover {
  transform: rotateY(-14deg) translateZ(7px) translateY(-10px);
  box-shadow: 12px 18px 24px rgba(15, 23, 42, 0.3);
}

.cover-design {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 9px;
  width: 100%;
}

.pending-badge {
  max-width: 100%;
  font-size: 10px;
  font-weight: 800;
  color: #fff8f0;
  background: rgba(220, 38, 38, 0.82);
  border: 1px solid rgba(255, 255, 255, 0.35);
  border-radius: 3px;
  padding: 3px 6px;
  backdrop-filter: blur(4px);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: pointer;
  font-family: inherit;
}

.genre-badge {
  max-width: 100%;
  font-size: 11px;
  color: rgba(255, 255, 255, 0.96);
  background: rgba(37, 37, 37, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.24);
  border-radius: 3px;
  padding: 3px 6px;
  backdrop-filter: blur(4px);
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.book-title {
  margin: 6px 0 0 0 !important;
  font-size: 17px !important;
  font-weight: 800;
  line-height: 1.35;
  color: var(--color-bg-surface) !important;
  text-shadow: 0 2px 5px rgba(72, 50, 30, 0.28);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-all;
  white-space: normal !important;
  cursor: pointer;
  transition: color 0.15s ease;
}

.book-title:hover {
  text-decoration: underline;
  color: #ffe1d1 !important;
}

.book-author-label {
  margin: 2px 0 0;
  font-size: 12px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.88);
  text-shadow: 0 1px 3px rgba(72, 50, 30, 0.35);
}

.cover-footer {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  gap: 10px;
  width: 100%;
}

.book-meta {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.meta-inline-stats {
  margin: 0;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 6px;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.4;
  color: rgba(255, 255, 255, 0.94);
}

.meta-inline-item {
  white-space: nowrap;
}

.meta-sep {
  font-weight: 400;
  opacity: 0.45;
  user-select: none;
}

.meta-updated {
  margin: 0;
  font-size: 11px;
  font-weight: 600;
  line-height: 1.35;
  color: rgba(255, 255, 255, 0.78);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.cover-footer-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.14);
  padding-top: 8px;
  width: 100%;
}

.meta-time {
  font-size: 11px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.04em;
  color: rgba(255, 255, 255, 0.82);
  text-shadow: 0 1px 3px rgba(40, 28, 18, 0.35);
  flex-shrink: 0;
}

.meta-time--empty {
  opacity: 0.45;
  font-weight: 600;
}

.book-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.action-btn {
  color: rgba(255, 255, 255, 0.75) !important;
  padding: 0 !important;
  height: 24px !important;
  width: 24px !important;
  margin: 0 !important;
  font-size: 14px !important;
  transition: all 0.2s ease;
  display: inline-flex;
  justify-content: center;
  align-items: center;
  border-radius: 4px !important;
}

.action-btn:hover {
  color: var(--color-bg-surface) !important;
  background: rgba(255, 255, 255, 0.18) !important;
}

.action-btn.delete-btn:hover {
  color: #ff5e62 !important;
}
</style>