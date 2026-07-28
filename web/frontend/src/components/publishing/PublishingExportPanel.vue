<script setup lang="ts">
import { Check, Download, DocumentCopy, Warning } from '@element-plus/icons-vue'

import type {
  ExportFormat,
  PublishingWorkspace,
} from '../../entities/publishing/publishing'

defineProps<{
  workspace: PublishingWorkspace
  selectedChapterId: string
  exporting: boolean
}>()
const format = defineModel<ExportFormat>('format', { required: true })
const scope = defineModel<'all' | 'chapter'>('scope', { required: true })
const title = defineModel<string>('title', { required: true })
const emit = defineEmits<{
  download: []
  navigate: [route: string]
}>()
</script>

<template>
  <section class="export-grid">
    <article class="export-builder">
      <header>
        <div class="export-icon"><Download /></div>
        <div><h2>生成成书文件</h2><p>一次确认后，从当前已保存的数据库文稿生成。</p></div>
      </header>

      <label class="field">
        <span>书名</span>
        <el-input v-model="title" maxlength="200" show-word-limit />
      </label>

      <div class="field">
        <span>导出范围</span>
        <el-radio-group v-model="scope">
          <el-radio-button value="all">全书 {{ workspace.book.chapter_count }} 章</el-radio-button>
          <el-radio-button value="chapter" :disabled="!selectedChapterId">
            当前第 {{ selectedChapterId || '—' }} 章
          </el-radio-button>
        </el-radio-group>
      </div>

      <div class="field">
        <span>文件格式</span>
        <div class="format-grid">
          <button
            v-for="item in workspace.formats"
            :key="item.id"
            type="button"
            :disabled="!item.available"
            :class="{ active: format === item.id }"
            @click="format = item.id"
          >
            <strong>{{ item.label }}</strong>
            <small>{{ item.extension }}</small>
            <em>{{ item.available ? '可用' : '组件未安装' }}</em>
          </button>
        </div>
      </div>

      <div class="export-note">
        <DocumentCopy />
        <p>
          TXT 与 Markdown 适合备份和平台粘贴；DOCX 适合编辑交付；EPUB 3 适合电子书阅读；
          PDF 使用内置中文字体，适合固定版式预览。
        </p>
      </div>

      <el-button
        type="primary"
        size="large"
        :icon="Download"
        :loading="exporting"
        :disabled="!workspace.preflight.can_export"
        @click="emit('download')"
      >
        检查并下载
      </el-button>
    </article>

    <aside class="preflight-panel">
      <header>
        <div>
          <h2>发布前检查</h2>
          <p>阻断项必须处理；提示项可在确认后继续导出。</p>
        </div>
        <span
          :class="{
            danger: workspace.preflight.blocking_count,
            warning: !workspace.preflight.blocking_count && workspace.preflight.warning_count,
          }"
        >
          {{
            workspace.preflight.blocking_count
              ? '暂不可导出'
              : workspace.preflight.warning_count
                ? '确认后可导出'
                : '全部就绪'
          }}
        </span>
      </header>
      <div class="preflight-list">
        <div
          v-for="item in workspace.preflight.items"
          :key="item.code"
          :class="item.severity"
        >
          <el-icon>
            <Check v-if="item.severity === 'ready'" />
            <Warning v-else />
          </el-icon>
          <div><strong>{{ item.label }}</strong><p>{{ item.detail }}</p></div>
          <button
            v-if="item.route"
            type="button"
            @click="emit('navigate', item.route)"
          >
            去处理
          </button>
        </div>
      </div>
      <footer>
        <strong>数据来源</strong>
        <span>SQLite 文稿 · 当前保存版本</span>
        <strong>临时文件</strong>
        <span>下载响应结束后自动清理</span>
      </footer>
    </aside>
  </section>
</template>

<style scoped>
.export-grid { display: grid; min-height: 100%; grid-template-columns: minmax(0, 1.2fr) minmax(330px, .8fr); gap: 10px; padding: 10px; overflow: auto; background: var(--color-bg-surface-muted); }
.export-builder, .preflight-panel { align-self: start; padding: 18px; border: 1px solid var(--color-border); border-radius: 12px; background: var(--color-bg-surface); box-shadow: var(--shadow-sm); }
.export-builder > header { display: flex; align-items: center; gap: 11px; margin-bottom: 18px; }
.export-icon { display: grid; width: 38px; height: 38px; place-items: center; border-radius: 10px; background: var(--color-primary-soft); color: var(--color-primary); }
h2 { margin: 0; color: var(--color-text-strong); font-size: 15px; }
header p { margin: 3px 0 0; color: var(--color-text-muted); font-size: 10px; }
.field { display: grid; gap: 7px; margin-bottom: 16px; }
.field > span { color: var(--color-text-strong); font-size: 10px; font-weight: 800; }
.format-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 7px; }
.format-grid button { display: grid; gap: 2px; padding: 10px 8px; border: 1px solid var(--color-border); border-radius: 9px; background: var(--color-bg-surface); color: var(--color-text-muted); cursor: pointer; text-align: left; }
.format-grid button:hover:not(:disabled), .format-grid button.active { border-color: var(--color-primary); background: var(--color-primary-soft); }
.format-grid button:disabled { opacity: .48; cursor: not-allowed; }
.format-grid strong { color: var(--color-text-strong); font-size: 11px; }
.format-grid small { font-size: 9px; }
.format-grid em { margin-top: 4px; color: var(--color-success); font-size: 8px; font-style: normal; }
.format-grid button:disabled em { color: var(--color-warning); }
.export-note { display: flex; gap: 9px; margin: 4px 0 18px; padding: 11px; border-radius: 9px; background: var(--color-info-soft); color: var(--color-info); }
.export-note svg { width: 16px; flex: 0 0 16px; }
.export-note p { margin: 0; font-size: 9px; line-height: 1.65; }
.preflight-panel > header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; padding-bottom: 14px; border-bottom: 1px solid var(--color-border); }
.preflight-panel > header > span { flex: 0 0 auto; padding: 5px 8px; border-radius: 999px; background: var(--color-success-soft); color: var(--color-success); font-size: 8px; font-weight: 800; }
.preflight-panel > header > span.warning { background: var(--color-warning-soft); color: var(--color-warning); }
.preflight-panel > header > span.danger { background: var(--color-danger-soft); color: var(--color-danger); }
.preflight-list { display: grid; gap: 8px; padding: 12px 0; }
.preflight-list > div { display: grid; grid-template-columns: 24px minmax(0, 1fr) auto; align-items: start; gap: 8px; padding: 9px; border: 1px solid var(--color-border); border-radius: 8px; }
.preflight-list .el-icon { width: 22px; height: 22px; border-radius: 7px; background: var(--color-success-soft); color: var(--color-success); }
.preflight-list .warning .el-icon { background: var(--color-warning-soft); color: var(--color-warning); }
.preflight-list .blocking .el-icon { background: var(--color-danger-soft); color: var(--color-danger); }
.preflight-list > div > div { display: grid; gap: 2px; }
.preflight-list strong { color: var(--color-text-strong); font-size: 10px; }
.preflight-list p { margin: 0; color: var(--color-text-muted); font-size: 9px; line-height: 1.5; }
.preflight-list button { border: 0; background: transparent; color: var(--color-primary); cursor: pointer; font-size: 9px; font-weight: 800; }
.preflight-panel footer { display: grid; grid-template-columns: auto 1fr; gap: 5px 10px; padding-top: 12px; border-top: 1px solid var(--color-border); font-size: 9px; }
.preflight-panel footer strong { color: var(--color-text-strong); }
.preflight-panel footer span { color: var(--color-text-muted); }
@media (max-width: 930px) {
  .export-grid { grid-template-columns: 1fr; }
  .format-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
</style>
