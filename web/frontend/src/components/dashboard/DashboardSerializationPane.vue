<script setup lang="ts">
import { Check, ChatLineRound, Download, Refresh, Warning } from '@element-plus/icons-vue'
import { useTasksStore } from '../../stores/tasks'

defineProps<{
  serialStatus: {
    today_word_count: number
    authoritative_completed: number
    disk_chapters_with_final: number
    library_indexed: number
    pending_candidates_count: number
    avg_bounce_rate: number
    crisis_level: string
    progress_note?: string
  }
  virtualComments: any[]
  rewritingOutline: boolean
  copyingTrial: boolean
  exportingSerial: boolean
}>()

const emit = defineEmits<{
  refresh: []
  triggerRewrite: []
  copyTrial: []
  download: [format: string]
}>()

const tasksStore = useTasksStore()
</script>

<template>
  <div class="serialization-pane">
    <el-alert
      type="info"
      :closable="false"
      show-icon
      class="serial-advanced-hint"
      title="日常写书可忽略本页"
      description="纠偏大纲、叙事债、连载导出等进阶能力；日常只需「创作工作台」+ 章节维护。"
    />

    <section class="serial-overview-cards">
      <div class="serial-stat-card">
        <span class="stat-label">今日连载字数</span>
        <strong class="stat-val text-primary">{{ serialStatus.today_word_count }}</strong>
        <span class="stat-tip">今日更新的汉字总数</span>
      </div>
      <div class="serial-stat-card">
        <span class="stat-label">全书批量已完成（权威）</span>
        <strong class="stat-val text-info">
          {{ serialStatus.authoritative_completed }} <small>章</small>
        </strong>
        <span class="stat-tip">与大纲页进度摘要 novel_batch_progress 一致</span>
      </div>
      <div class="serial-stat-card">
        <span class="stat-label">磁盘有正文 / 书库索引</span>
        <strong class="stat-val">
          {{ serialStatus.disk_chapters_with_final }} / {{ serialStatus.library_indexed }}
        </strong>
        <span class="stat-tip">正文目录数 · SQLite 章数（参考）</span>
      </div>
      <div class="serial-stat-card">
        <span class="stat-label">待审批设定变更</span>
        <strong
          class="stat-val"
          :class="serialStatus.pending_candidates_count > 0 ? 'text-warning' : 'text-success'"
        >
          {{ serialStatus.pending_candidates_count }} <small>个</small>
        </strong>
        <span class="stat-tip">暂存状态的 Pending Candidate</span>
      </div>
      <div class="serial-stat-card">
        <span class="stat-label">读者流失指标</span>
        <strong
          class="stat-val"
          :class="
            serialStatus.crisis_level === '正常'
              ? 'text-success'
              : serialStatus.crisis_level === '中度警戒'
                ? 'text-warning'
                : 'text-danger'
          "
        >
          {{ (serialStatus.avg_bounce_rate * 100).toFixed(1) }}%
        </strong>
        <span
          class="stat-badge"
          :class="
            serialStatus.crisis_level === '正常'
              ? 'badge-success'
              : serialStatus.crisis_level === '中度警戒'
                ? 'badge-warning'
                : 'badge-danger'
          "
        >
          {{ serialStatus.crisis_level }}
        </span>
      </div>
    </section>

    <section v-if="serialStatus.crisis_level !== '正常'" class="crisis-alert-banner">
      <div class="alert-left">
        <el-icon class="alert-icon pulse"><Warning /></el-icon>
        <div class="alert-text">
          <h3>【大纲自适应纠偏警告】：读者流失过高！</h3>
          <p>
            当前读者流失表现为 <strong>{{ serialStatus.crisis_level }}</strong
            >。反馈指出节奏拖沓、爽点匮乏。建议立刻让 AI 主编根据读者吐槽对后续章节大纲进行自适应纠偏！
          </p>
        </div>
      </div>
      <el-button
        type="danger"
        :loading="rewritingOutline"
        :disabled="tasksStore.isRunning || rewritingOutline"
        @click="emit('triggerRewrite')"
      >
        一键大纲纠偏
      </el-button>
    </section>

    <div class="serial-workspace">
      <article class="serial-column comment-area">
        <div class="column-header">
          <h3><el-icon><ChatLineRound /></el-icon> 读者模拟评论区</h3>
          <el-button size="small" :icon="Refresh" @click="emit('refresh')">刷新评论</el-button>
        </div>

        <div class="comments-list-wrapper">
          <div v-if="virtualComments.length === 0" class="empty-placeholder">
            <p>暂无读者评论。请先生成章节，系统将根据跳出率模拟真实书评吐槽。</p>
          </div>
          <div v-else class="comments-scroll-list">
            <div v-for="c in virtualComments" :key="c.id" class="comment-card">
              <div class="comment-card-head">
                <img
                  :src="c.avatar || 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png'"
                  class="comment-avatar"
                  alt="avatar"
                />
                <div class="comment-author-info">
                  <div class="author-row">
                    <span class="author-name">{{ c.author }}</span>
                    <span class="chapter-tag">{{ c.chapter_label }}</span>
                  </div>
                  <div class="rating-row">
                    <span class="rating-stars">{{ c.rating }}</span>
                    <span class="comment-time">{{ c.created_at }}</span>
                  </div>
                </div>
              </div>
              <p class="comment-content">{{ c.content }}</p>
              <div class="comment-card-foot">
                <span class="likes-count">👍 {{ c.likes }} 点赞</span>
              </div>
            </div>
          </div>
        </div>
      </article>

      <article class="serial-column pending-states-area">
        <div class="column-header column-header-split">
          <h3 class="column-title-with-icon"><el-icon><Check /></el-icon> 设定自动同步</h3>
          <span class="badge">默认自动通过</span>
        </div>

        <div class="states-list-wrapper">
          <div class="empty-placeholder">
            <el-icon class="success-icon"><Check /></el-icon>
            <p>当前实体设定会在生成完成后自动通过并同步，无需人工审批。</p>
          </div>
        </div>
      </article>
    </div>

    <section class="serial-export-footer">
      <div class="export-text">
        <h3>一键导出已更新连载包</h3>
        <p>导出所有已物理生成的正式章节正文，打包为压缩包(ZIP)或合并为单文本(TXT)。</p>
      </div>
      <div class="export-actions">
        <el-button type="warning" plain :loading="copyingTrial" @click="emit('copyTrial')">
          复制试发（剪贴板）
        </el-button>
        <el-button
          type="success"
          :icon="Download"
          :loading="exportingSerial"
          @click="emit('download', 'txt')"
        >
          缝合单文本 (TXT)
        </el-button>
        <el-button
          type="primary"
          :icon="Download"
          :loading="exportingSerial"
          @click="emit('download', 'zip')"
        >
          打包分章压缩包 (ZIP)
        </el-button>
      </div>
      <p v-if="serialStatus.progress_note" class="serial-progress-note">
        {{ serialStatus.progress_note }}
      </p>
    </section>
  </div>
</template>

<style scoped>
.serialization-pane {
  display: flex;
  flex-direction: column;
}

.serial-advanced-hint {
  margin-bottom: 14px;
}

.serial-overview-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.serial-stat-card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  position: relative;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.02);
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.serial-stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}

.stat-label {
  font-size: 13px;
  color: var(--color-text-muted);
  font-weight: 600;
  margin-bottom: 6px;
}

.stat-val {
  font-size: 28px;
  font-weight: 850;
  color: var(--color-text-strong);
  line-height: 1.2;
}

.stat-val small {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-muted);
}

.stat-tip {
  font-size: 11.5px;
  color: var(--color-text-subtle);
  margin-top: 8px;
}

.stat-badge {
  position: absolute;
  top: 18px;
  right: 18px;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 999px;
  font-weight: 700;
}

.badge-success {
  background: #ecfdf5;
  color: var(--color-success);
}

.badge-warning {
  background: #fffbeb;
  color: var(--color-warning);
}

.badge-danger {
  background: #fef2f2;
  color: var(--color-danger);
}

.text-primary {
  color: var(--color-primary) !important;
}

.text-info {
  color: #06b6d4 !important;
}

.text-success {
  color: var(--color-success) !important;
}

.text-warning {
  color: var(--color-warning) !important;
}

.text-danger {
  color: var(--color-danger) !important;
}

.crisis-alert-banner {
  background: linear-gradient(90deg, #fef2f2 0%, #fff5f5 100%);
  border: 1px solid #fee2e2;
  border-radius: 12px;
  padding: 16px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

.alert-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.alert-icon {
  font-size: 28px;
  color: var(--color-danger);
}

.pulse {
  animation: pulse-warn 1.8s infinite;
}

@keyframes pulse-warn {
  0% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.15);
    opacity: 0.8;
  }
  100% {
    transform: scale(1);
  }
}

.alert-text h3 {
  margin: 0;
  font-size: 15.5px;
  font-weight: 800;
  color: #991b1b;
}

.alert-text p {
  margin: 4px 0 0;
  font-size: 13.5px;
  color: #7f1d1d;
  line-height: 1.45;
}

.serial-workspace {
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 20px;
  margin-bottom: 20px;
}

.serial-column {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  height: 520px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.01);
}

.column-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--color-bg-hover);
  background: var(--color-bg-surface-muted);
}

.column-header-split {
  width: 100%;
}

.column-header h3,
.column-title-with-icon {
  margin: 0;
  font-size: 15px;
  font-weight: 800;
  color: var(--color-text-strong);
  display: flex;
  align-items: center;
  gap: 6px;
}

.column-header .badge {
  background: var(--color-border);
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
}

.comments-list-wrapper,
.states-list-wrapper {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: #fcfdfe;
}

.empty-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-subtle);
  font-size: 13.5px;
  text-align: center;
  padding: 30px;
}

.success-icon {
  font-size: 42px;
  color: var(--color-success);
  background: #ecfdf5;
  padding: 12px;
  border-radius: 50%;
  margin-bottom: 12px;
}

.comments-scroll-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.comment-card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-bg-hover);
  border-radius: 10px;
  padding: 14px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.01);
  transition: border-color 0.2s, transform 0.2s;
}

.comment-card:hover {
  border-color: var(--color-border);
  transform: translateY(-1px);
}

.comment-card-head {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 8px;
}

.comment-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--color-bg-hover);
  border: 1px solid var(--color-border);
}

.comment-author-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.author-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.author-name {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--color-text);
}

.chapter-tag {
  font-size: 11px;
  background: var(--color-primary-soft);
  color: var(--color-primary-hover);
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 700;
}

.rating-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 2px;
}

.rating-stars {
  color: var(--color-warning);
  font-size: 11px;
}

.comment-time {
  font-size: 11px;
  color: var(--color-text-subtle);
}

.comment-content {
  margin: 6px 0 8px;
  font-size: 13px;
  color: var(--color-text-muted);
  line-height: 1.5;
  white-space: pre-wrap;
}

.comment-card-foot {
  display: flex;
  justify-content: flex-end;
  font-size: 11.5px;
  color: var(--color-text-muted);
}

.serial-export-footer {
  background: linear-gradient(135deg, var(--color-bg-surface-muted) 0%, var(--color-bg-hover) 100%);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 20px 24px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-top: 20px;
  margin-bottom: 8px;
  box-shadow: 0 6px 20px -12px rgba(15, 23, 42, 0.08);
}

.serial-progress-note {
  margin: 10px 0 0;
  width: 100%;
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.45;
}

.export-text h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 850;
  color: var(--color-text-strong);
}

.export-text p {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--color-text-muted);
}

.export-actions {
  display: flex;
  gap: 12px;
}

@media (max-width: 1200px) {
  .serial-overview-cards {
    grid-template-columns: repeat(2, 1fr);
  }

  .serial-workspace {
    grid-template-columns: 1fr;
  }
}
</style>