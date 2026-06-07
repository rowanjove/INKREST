<script setup lang="ts">
import { Plus } from '@element-plus/icons-vue'
import AiBubbleMenu from '../AiBubbleMenu.vue'

defineProps<{
  bubbleX: number
  bubbleY: number
  selectedText: string
  activeChapterId: string
  currentChapter: any | null
  snapshotsList: any[]
  loadingSnapshots: boolean
  previewingSnapshot: any | null
  versionsList: any[]
  compareVersionId: string
  diffChunks: Array<{ type: string; text: string }>
  loadingDiff: boolean
  writing: boolean
  onAcceptRewrite: (text: string) => void
  onTriggerExpand: () => void
  onAcceptExpand: () => void
  onManualSnapshot: () => void
  onPreviewSnapshot: (snap: any) => void
  onRollback: (snap: any) => void
  onActivateVersion: () => void
  onStartAiWrite: () => void
}>()

const showBubble = defineModel<boolean>('showBubble', { required: true })
const showExpandDialog = defineModel<boolean>('showExpandDialog', { required: true })
const expandResult = defineModel<string>('expandResult', { required: true })
const timeMachineOpen = defineModel<boolean>('timeMachineOpen', { required: true })
const showPreviewDialog = defineModel<boolean>('showPreviewDialog', { required: true })
const compareDialogOpen = defineModel<boolean>('compareDialogOpen', { required: true })
const writeDialogOpen = defineModel<boolean>('writeDialogOpen', { required: true })
const chapterGoalForWrite = defineModel<string>('chapterGoalForWrite', { required: true })
</script>

<template>
  <AiBubbleMenu
    :visible="showBubble"
    :x="bubbleX"
    :y="bubbleY"
    :selected-text="selectedText"
    :chapter-id="activeChapterId"
    :chapter-goal="currentChapter?.plan?.chapter_goal || ''"
    @accept="onAcceptRewrite"
    @close="showBubble = false"
    @expand="onTriggerExpand"
  />

  <el-dialog
    v-model="showExpandDialog"
    title="🚀 AI 续写段落预览"
    width="450px"
    :close-on-click-modal="false"
  >
    <div class="expand-dialog-body">
      <div class="expand-result-box">
        {{ expandResult }}
      </div>
      <p class="dialog-tips">您可以选择采纳并直接插入到当前光标所在位置，或点击放弃。</p>
    </div>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="showExpandDialog = false; expandResult = ''">放弃</el-button>
        <el-button type="primary" @click="onAcceptExpand">采纳并插入</el-button>
      </span>
    </template>
  </el-dialog>

  <el-drawer
    v-model="timeMachineOpen"
    title="⏳ 版本时光机"
    direction="rtl"
    size="380px"
    :append-to-body="true"
  >
    <div class="time-machine-drawer" v-loading="loadingSnapshots">
      <div style="margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
        <span style="font-size: 12px; color: var(--color-text-muted);">本地保留最近 30 次自动与手动备份</span>
        <el-button type="primary" size="small" :icon="Plus" @click="onManualSnapshot">新建快照</el-button>
      </div>

      <el-empty v-if="snapshotsList.length === 0" description="暂无历史版本备份" :image-size="60" />
      <div v-else class="snapshots-list">
        <div
          v-for="snap in snapshotsList"
          :key="snap.timestamp"
          class="snapshot-card"
          :class="{ manual: snap.is_manual }"
        >
          <div class="snapshot-card-header">
            <span class="snapshot-title">{{ snap.title }}</span>
            <el-tag size="small" :type="snap.is_manual ? 'primary' : 'info'">
              {{ snap.is_manual ? '手动' : '自动' }}
            </el-tag>
          </div>
          <div class="snapshot-meta">
            <span>📅 {{ snap.datetime }}</span>
            <span>🔤 {{ snap.word_count }} 字</span>
          </div>
          <div class="snapshot-actions">
            <el-button size="small" link type="primary" @click="onPreviewSnapshot(snap)">预览正文</el-button>
            <el-button size="small" link type="warning" @click="onRollback(snap)">回滚到此版本</el-button>
          </div>
        </div>
      </div>
    </div>
  </el-drawer>

  <el-dialog
    v-model="showPreviewDialog"
    :title="`预览备份: ${previewingSnapshot?.title || ''}`"
    width="600px"
    :append-to-body="true"
  >
    <div class="snapshot-preview-dialog-body" v-if="previewingSnapshot">
      <div class="preview-meta-bar">
        <span>备份时间：{{ previewingSnapshot.datetime }}</span>
        <span>字数统计：{{ previewingSnapshot.word_count }} 字</span>
      </div>
      <div class="preview-text-box">
        {{ previewingSnapshot.final_text || '（空正文）' }}
      </div>
    </div>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="showPreviewDialog = false">关闭预览</el-button>
        <el-button type="warning" @click="onRollback(previewingSnapshot)">回滚到此版本</el-button>
      </span>
    </template>
  </el-dialog>

  <el-dialog
    v-model="compareDialogOpen"
    :title="`剧情分支比对: 正史版本 vs ${versionsList.find(v => v.id === compareVersionId)?.version_name || ''}`"
    width="750px"
    align-center
  >
    <div v-loading="loadingDiff" class="diff-dialog-body" style="max-height: 480px; overflow-y: auto; padding: 12px;">
      <div class="diff-legend" style="margin-bottom: 12px; display: flex; gap: 14px; font-size: 12px;">
        <span>标注说明:</span>
        <span style="color:var(--color-success); background-color:#d1fae5; padding:2px 6px; border-radius:4px; font-weight:600;">绿色表示分支新增字句</span>
        <span style="color:var(--color-danger); background-color:#fee2e2; padding:2px 6px; border-radius:4px; text-decoration:line-through;">红色表示分支删除/改写字句</span>
      </div>
      <div class="diff-container" style="white-space: pre-wrap; line-height: 1.8; font-size: 14px; background: #fafaf9; padding: 16px; border-radius: 8px; border: 1px solid var(--color-border);">
        <template v-for="(chunk, idx) in diffChunks" :key="idx">
          <span v-if="chunk.type === 'equal'" class="diff-text equal">{{ chunk.text }}</span>
          <del v-else-if="chunk.type === 'delete'" class="diff-text delete">{{ chunk.text }}</del>
          <ins v-else-if="chunk.type === 'insert'" class="diff-text insert">{{ chunk.text }}</ins>
        </template>
      </div>
    </div>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="compareDialogOpen = false">关闭比对</el-button>
        <el-button type="success" @click="compareDialogOpen = false; onActivateVersion()">采纳该分支为正史</el-button>
      </span>
    </template>
  </el-dialog>

  <el-dialog
    v-model="writeDialogOpen"
    title="🤖 AI 快速写作"
    width="500px"
    :close-on-click-modal="false"
  >
    <div style="display: flex; flex-direction: column; gap: 12px;">
      <p style="margin: 0; font-size: 13px; color: var(--color-text-muted); line-height: 1.6;">
        本功能将根据您设定的章节大纲目标，由 AI 快速撰写并填满当前章节。您可以对预设目标进行修改调整。
      </p>
      <el-input
        v-model="chapterGoalForWrite"
        type="textarea"
        :rows="6"
        placeholder="请输入本章详细的大纲与写作目标，例如：交代主角在坊市购买符笔的经过，并遇到竞争对手刁难..."
      />
    </div>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="writeDialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="writing" @click="onStartAiWrite">开始写作</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<style scoped>
.expand-result-box::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
.expand-result-box::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.3);
  border-radius: 99px;
}
.expand-result-box::-webkit-scrollbar-thumb:hover {
  background: rgba(148, 163, 184, 0.5);
}

.expand-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.expand-result-box {
  background: var(--color-bg-surface-muted);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 18px;
  font-size: 14px;
  line-height: 1.8;
  color: var(--color-text);
  white-space: pre-wrap;
  max-height: 280px;
  overflow-y: auto;
}
.dialog-tips {
  font-size: 12px;
  color: var(--color-text-muted);
  margin: 0;
}

.time-machine-drawer {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.snapshots-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  flex: 1;
  padding-bottom: 20px;
}
.snapshot-card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: all 0.2s;
}
.snapshot-card:hover {
  border-color: var(--color-border);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
}
.snapshot-card.manual {
  border-left: 3px solid var(--color-primary);
}
.snapshot-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.snapshot-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text-strong);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 220px;
}
.snapshot-meta {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--color-text-muted);
}
.snapshot-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  border-top: 1px solid var(--color-bg-hover);
  padding-top: 8px;
  margin-top: 4px;
}

.snapshot-preview-dialog-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.preview-meta-bar {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--color-text-muted);
  background: var(--color-bg-surface-muted);
  padding: 8px 12px;
  border-radius: 6px;
}
.preview-text-box {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 16px;
  font-size: 14px;
  line-height: 1.8;
  color: var(--color-text);
  white-space: pre-wrap;
  max-height: 400px;
  overflow-y: auto;
}

.diff-container .diff-text.equal {
  color: var(--color-text);
}
.diff-container .diff-text.delete {
  color: var(--color-danger);
  background-color: #fee2e2;
  text-decoration: line-through;
  padding: 2px 0;
  border-radius: 2px;
  display: inline;
}
.diff-container .diff-text.insert {
  color: var(--color-success);
  background-color: #d1fae5;
  text-decoration: none;
  font-weight: 600;
  padding: 2px 0;
  border-radius: 2px;
  display: inline;
}
</style>