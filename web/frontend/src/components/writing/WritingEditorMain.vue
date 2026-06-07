<script setup lang="ts">
import type { ComponentPublicInstance } from 'vue'
import { Delete, Check } from '@element-plus/icons-vue'
import { useTasksStore } from '../../stores/tasks'
import type { WriteTheme } from '../../composables/useWritingVisualSettings'

const props = defineProps<{
  setEditorRef: (el: HTMLTextAreaElement | null) => void
  loadingEditor: boolean
  currentChapter: any | null
  platformsList: any[]
  activePlatform: string
  activePlatformLabel: string
  versionsList: any[]
  activeVersion: any | undefined
  saving: boolean
  onPlatformChange: (name: string) => void
  onVersionChange: (id: string) => void
  onOpenCompare: (id: string) => void
  onDeleteVersion: (id: string) => void
  onCreateVersion: () => void
  onActivateVersion: () => void
  onAutoFormat: () => void
  onManualSnapshot: () => void
  onSave: () => void
  onForceRefresh: () => void
  onOpenTimeMachine: () => void
  onTriggerWrite: () => void
  onKeyDown: (event: KeyboardEvent) => void
  onTextSelection: (event: MouseEvent | KeyboardEvent) => void
  onAdjustTextareaHeight: () => void
}>()

const editorText = defineModel<string>('editorText', { required: true })
const writeTheme = defineModel<WriteTheme>('writeTheme', { required: true })
const writeFontSize = defineModel<number>('writeFontSize', { required: true })
const writeLineHeight = defineModel<number>('writeLineHeight', { required: true })
const writeIndent = defineModel<boolean>('writeIndent', { required: true })
const writeTitleCenter = defineModel<boolean>('writeTitleCenter', { required: true })

const tasksStore = useTasksStore()

function bindEditorRef(el: Element | ComponentPublicInstance | null) {
  props.setEditorRef(el as HTMLTextAreaElement | null)
}
</script>

<template>
  <div class="editor-workspace">
    <div class="editor-main-container" v-loading="loadingEditor">
      <div class="editor-header-actions glass-panel">
        <div class="left-chapter-meta" style="display: flex; align-items: center; gap: 10px; flex-shrink: 0; min-width: 200px;">
          <div class="chapter-info">
            <span v-if="editorText" class="wc-label">共 <strong>{{ editorText.length }}</strong> 字符</span>
          </div>

          <div v-if="platformsList.length > 0" class="platform-selector-container" style="display: flex; align-items: center; gap: 6px; margin-left: 16px;">
            <el-dropdown trigger="click" @command="onPlatformChange">
              <el-button size="small" type="success" plain class="premium-btn">
                🎯 平台: {{ activePlatformLabel }}
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item
                    v-for="p in platformsList"
                    :key="p.name"
                    :command="p.name"
                    :disabled="activePlatform === p.name"
                  >
                    <div style="width: 240px; display: flex; flex-direction: column; white-space: normal; padding: 6px 0; align-items: flex-start; text-align: left;">
                      <span style="font-weight: 600; font-size: 13px; color: var(--color-text-strong); display: flex; align-items: center; gap: 4px;">
                        🎯 {{ p.label }}
                      </span>
                      <div style="font-size: 11px; color: var(--color-text-muted); margin-top: 4px; line-height: 1.4; word-break: break-all;">
                        {{ p.style_prompt }}
                      </div>
                    </div>
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>

          <div v-if="versionsList.length > 0" class="version-selector-container" style="display: flex; align-items: center; gap: 6px; margin-left: 12px;">
            <el-dropdown trigger="click" @command="onVersionChange">
              <el-button size="small" type="warning" plain class="premium-btn">
                🌿 分支: {{ activeVersion?.version_name || '未命名' }}
                <span v-if="activeVersion?.is_active" style="margin-left:4px;font-size:10px;color:#67c23a;">(正史)</span>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item
                    v-for="v in versionsList"
                    :key="v.id"
                    :command="v.id"
                  >
                    <div class="ver-item-drop" style="display:flex; align-items:center; justify-content:space-between; width:220px; gap:8px;">
                      <div style="flex:1; overflow:hidden;">
                        <div style="font-weight:600; font-size:13px; text-overflow:ellipsis; overflow:hidden; white-space:nowrap;">
                          {{ v.version_name }}
                          <span v-if="v.is_active" style="margin-left:4px; color:#67c23a; font-size:10px;">[正史]</span>
                        </div>
                        <div style="font-size:11px; color:#909399; text-overflow:ellipsis; overflow:hidden; white-space:nowrap;" v-if="v.note">{{ v.note }}</div>
                      </div>
                      <div style="display:flex; gap:2px; flex-shrink:0;">
                        <el-button size="small" type="primary" link :icon="Check" v-if="!v.is_active" @click.stop="onOpenCompare(v.id)" title="比对正史" style="padding:0 2px;" />
                        <el-button size="small" type="danger" link :icon="Delete" v-if="!v.is_active" @click.stop="onDeleteVersion(v.id)" title="删除分支" style="padding:0 2px;" />
                      </div>
                    </div>
                  </el-dropdown-item>
                  <el-dropdown-item divided :command="null" @click="onCreateVersion" style="color:var(--el-color-primary);">
                    ✨ 新建分支试写...
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button
              v-if="activeVersion && activeVersion.is_active === 0"
              size="small"
              type="success"
              @click="onActivateVersion"
              title="采纳为本章的正史版本"
            >
              采纳为正史
            </el-button>
          </div>
        </div>
        <div class="action-buttons">
          <el-popover placement="bottom" title="排版与视觉设置" :width="240" trigger="click">
            <template #reference>
              <el-button size="default" class="premium-btn">⚙️ 排版</el-button>
            </template>
            <div class="typography-settings">
              <div class="setting-item">
                <span class="setting-label">护眼主题</span>
                <div class="theme-options">
                  <button class="theme-opt white" :class="{ active: writeTheme === 'white' }" @click="writeTheme = 'white'">白</button>
                  <button class="theme-opt parchment" :class="{ active: writeTheme === 'parchment' }" @click="writeTheme = 'parchment'">黄</button>
                  <button class="theme-opt green" :class="{ active: writeTheme === 'green' }" @click="writeTheme = 'green'">绿</button>
                  <button class="theme-opt dark" :class="{ active: writeTheme === 'dark' }" @click="writeTheme = 'dark'">黑</button>
                </div>
              </div>
              <div class="setting-item">
                <span class="setting-label">字体大小 ({{ writeFontSize }}px)</span>
                <el-slider v-model="writeFontSize" :min="14" :max="26" :step="1" />
              </div>
              <div class="setting-item">
                <span class="setting-label">行高比例 ({{ writeLineHeight }})</span>
                <el-slider v-model="writeLineHeight" :min="1.6" :max="2.6" :step="0.1" />
              </div>
              <div class="setting-item flex-between">
                <span class="setting-label">首行缩进 (两字符)</span>
                <el-switch v-model="writeIndent" />
              </div>
              <el-button type="primary" size="small" style="width: 100%; margin-top: 10px;" :disabled="tasksStore.isRunning" @click="onAutoFormat">一键排版</el-button>
            </div>
          </el-popover>

          <el-button
            type="info"
            size="default"
            class="premium-btn"
            :disabled="tasksStore.isRunning"
            @click="onManualSnapshot"
            title="保存手动快照"
          >
            💾 手动快照
          </el-button>

          <el-button
            size="default"
            class="premium-btn btn-save"
            :loading="saving"
            :disabled="tasksStore.isRunning"
            @click="onSave()"
          >
            💾 保存章节
          </el-button>

          <el-button
            type="info"
            size="default"
            class="premium-btn"
            @click="onForceRefresh"
            title="重新加载当前章节内容"
          >
            🔄 刷新
          </el-button>

          <el-button
            type="warning"
            size="default"
            class="premium-btn"
            @click="onOpenTimeMachine"
            title="版本时光机"
          >
            ⏳ 历史
          </el-button>
          <el-button
            type="primary"
            size="default"
            class="premium-btn btn-ai"
            :loading="loadingEditor"
            :disabled="tasksStore.isRunning"
            @click="onTriggerWrite"
          >
            <span class="ai-sparkle">🤖</span> AI 写作
          </el-button>
        </div>
      </div>

      <div class="textarea-scroll-container" :class="`theme-${writeTheme}`">
        <div class="zen-paper-sheet">
          <input
            v-if="currentChapter"
            v-model="currentChapter.title"
            class="chapter-title-input"
            :class="{ 'text-center': writeTitleCenter }"
            placeholder="请输入章节名称..."
          />
          <textarea
            :ref="bindEditorRef"
            v-model="editorText"
            class="zen-textarea"
            :class="{ 'indent-active': writeIndent }"
            :style="{ fontSize: `${writeFontSize}px`, lineHeight: writeLineHeight }"
            placeholder="在此开始你的小说创作吧... 支持拖动或选中文字使用 AI 智能润色修改。"
            @keydown="onKeyDown"
            @mouseup="onTextSelection"
            @keyup="onTextSelection"
            @input="onAdjustTextareaHeight"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.textarea-scroll-container::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
.textarea-scroll-container::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.3);
  border-radius: 99px;
}
.textarea-scroll-container::-webkit-scrollbar-thumb:hover {
  background: rgba(148, 163, 184, 0.5);
}

.editor-workspace {
  flex: 3;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: var(--color-bg-hover);
}

.editor-main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

.editor-header-actions.glass-panel {
  display: flex;
  justify-content: space-between;
  align-items: stretch;
  flex-wrap: wrap;
  gap: 12px;
  padding: 14px 24px;
  margin: 16px 24px 0;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.7);
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(12px);
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.04);
  z-index: 10;
  flex-shrink: 0;
}

.left-chapter-meta {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  min-width: 200px;
  width: 100%;
  flex-wrap: wrap;
}
.chapter-info h2 {
  margin: 0;
  font-size: 16px;
  color: var(--color-text-strong);
  font-weight: 800;
}
.wc-label {
  font-size: 11.5px;
  color: var(--color-text-muted);
  margin-top: 2px;
  display: block;
}

.action-buttons {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(84px, 1fr));
  gap: 10px;
  align-items: center;
  width: 100%;
  padding-top: 10px;
  border-top: 1px solid rgba(226, 232, 240, 0.85);
}
.action-buttons .premium-btn {
  width: 100%;
  margin: 0;
}
.premium-btn {
  border-radius: 8px !important;
  font-weight: 700 !important;
  transition: all 0.2s ease !important;
}
.premium-btn:hover {
  transform: translateY(-1px);
}
.btn-ai {
  background: var(--gradient-ai) !important;
  border: 0 !important;
  color: var(--color-bg-surface) !important;
  box-shadow: 0 4px 12px var(--color-primary-muted);
}
.btn-save {
  background: var(--gradient-save) !important;
  border: 0 !important;
  color: var(--color-bg-surface) !important;
  box-shadow: 0 4px 12px var(--color-success-soft);
}
.btn-save:hover {
  box-shadow: 0 6px 16px var(--color-success-soft);
}
.btn-ai {
  order: -1;
}
.btn-ai:hover {
  box-shadow: 0 6px 16px rgba(99, 102, 241, 0.35);
}
.ai-sparkle {
  margin-right: 4px;
}

.textarea-scroll-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px 40px;
  display: flex;
  justify-content: center;
  align-items: flex-start;
}

.zen-paper-sheet {
  width: 100%;
  max-width: 820px;
  min-height: 100%;
  height: auto;
  background: var(--color-bg-surface);
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.03);
  border: 1px solid rgba(226, 232, 240, 0.8);
  padding: 40px 50px 200px;
  box-sizing: border-box;
}

.chapter-title-input {
  width: 100%;
  border: none;
  outline: none;
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-strong);
  padding: 0 0 16px 0;
  margin-bottom: 20px;
  border-bottom: 2px dashed var(--color-border);
  background: transparent;
  font-family: inherit;
}
.chapter-title-input::placeholder {
  color: var(--color-text-subtle);
  font-weight: normal;
}

.zen-textarea {
  width: 100%;
  height: 100%;
  min-height: 500px;
  border: 0;
  resize: none;
  background: transparent;
  outline: none;
  font-family: "PingFang SC", "Lantinghei SC", "Microsoft YaHei", -apple-system, sans-serif;
  font-size: 16px;
  line-height: 2.0;
  letter-spacing: 0.03em;
  color: var(--color-text);
  padding: 0;
  box-sizing: border-box;
  overflow: hidden;
}

.textarea-scroll-container.theme-white {
  background: var(--color-bg-hover);
}
.textarea-scroll-container.theme-white .zen-paper-sheet {
  background: var(--color-bg-surface);
  border-color: rgba(226, 232, 240, 0.8);
}
.textarea-scroll-container.theme-white .zen-textarea,
.textarea-scroll-container.theme-white .chapter-title-input {
  color: var(--color-text);
}

.textarea-scroll-container.theme-parchment {
  background: #f1ebd9;
}
.textarea-scroll-container.theme-parchment .zen-paper-sheet {
  background: #fdfaf2;
  border-color: #e5d8b7;
  box-shadow: 0 10px 30px rgba(78, 52, 46, 0.05);
}
.textarea-scroll-container.theme-parchment .zen-textarea,
.textarea-scroll-container.theme-parchment .chapter-title-input {
  color: #4e342e;
}
.textarea-scroll-container.theme-parchment .chapter-title-input {
  border-bottom-color: #e5d8b7;
}

.textarea-scroll-container.theme-green {
  background: #d5ebd7;
}
.textarea-scroll-container.theme-green .zen-paper-sheet {
  background: #f1fcf3;
  border-color: #c0dfc5;
  box-shadow: 0 10px 30px rgba(27, 94, 32, 0.05);
}
.textarea-scroll-container.theme-green .zen-textarea,
.textarea-scroll-container.theme-green .chapter-title-input {
  color: #1b5e20;
}
.textarea-scroll-container.theme-green .chapter-title-input {
  border-bottom-color: #c0dfc5;
}

.textarea-scroll-container.theme-dark {
  background: var(--color-text-strong);
}
.textarea-scroll-container.theme-dark .zen-paper-sheet {
  background: var(--color-text-strong);
  border-color: var(--color-text);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
}
.textarea-scroll-container.theme-dark .zen-textarea,
.textarea-scroll-container.theme-dark .chapter-title-input {
  color: var(--color-border);
}
.textarea-scroll-container.theme-dark .chapter-title-input {
  border-bottom-color: var(--color-text);
}

.typography-settings {
  padding: 4px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.setting-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.setting-item.flex-between {
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
}
.setting-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted);
}
.theme-options {
  display: flex;
  gap: 6px;
}
.theme-opt {
  flex: 1;
  height: 28px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: 11px;
  cursor: pointer;
  outline: none;
  font-weight: 600;
  transition: all 0.2s;
}
.theme-opt.white { background: var(--color-bg-surface); color: var(--color-text); }
.theme-opt.parchment { background: #fdfaf2; color: #4e342e; border-color: #e5d8b7; }
.theme-opt.green { background: #f1fcf3; color: #1b5e20; border-color: #c0dfc5; }
.theme-opt.dark { background: var(--color-text-strong); color: var(--color-border); border-color: var(--color-text-muted); }
.theme-opt.active {
  border-color: var(--color-primary) !important;
  box-shadow: 0 0 0 2px var(--color-primary-muted);
}

.indent-active {
  text-indent: 2em;
}

.chapter-title-input.text-center {
  text-align: center;
}
</style>