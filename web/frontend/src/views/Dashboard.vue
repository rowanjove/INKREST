<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import {
  Delete,
  DocumentAdd,
  Plus,
  Check,
  Warning,
  Download,
  Refresh,
  ChatLineRound,
  Timer,
  WarningFilled,
} from '@element-plus/icons-vue'
import DashboardStats from '../components/DashboardStats.vue'
import ProjectReadinessCard from '../components/workbench/ProjectReadinessCard.vue'
import AgentProductionLine from '../components/workbench/AgentProductionLine.vue'
import ScaleArchitecturePanel from '../components/workbench/ScaleArchitecturePanel.vue'

import NovelBatchRunDialog from '../components/NovelBatchRunDialog.vue'
import { useNovelBatchRun } from '../composables/useNovelBatchRun'
import { useDashboardWorkbench } from '../composables/useDashboardWorkbench'
import { useDashboardSerial } from '../composables/useDashboardSerial'
import { useDashboardBatchDialog } from '../composables/useDashboardBatchDialog'
import { useDashboardPolling } from '../composables/useDashboardPolling'

import { useChapterStore } from '../stores/chapter'

const router = useRouter()
const chapterStore = useChapterStore()
const { loading } = storeToRefs(chapterStore)

const {
  assets,
  outline,
  engineStatus,
  semanticSearchEffective,
  vectorEnabledForProject,
  form,
  chapterCountTotal,
  calibration,
  scaleProfile,
  allDebt,
  outlineTheme,
  workScale,
  maxAvailableChapters,
  loadWorkbench,
  refreshScaleArchitecture,
} = useDashboardWorkbench()

const {
  serialStatus,
  copyingTrial,
  virtualComments,
  rewritingOutline,
  applyingOutline,
  outlineDiffDialogVisible,
  adaptiveOutlineDiff,
  exportingSerial,
  loadSerialData,
  triggerAdaptiveRewrite,
  applyAdaptive,
  copyTrialForPlatform,
  downloadSerial,
} = useDashboardSerial()

const {
  addChapterDialogVisible,
  addChapterTab,
  batchSubmitting,
  chapterPlanGenerating,
  batchInputMode,
  bulkText,
  chapterPlanCount,
  chapterPlanInstructions,
  batchRows,
  openAddChapterDialog,
  addBatchRow,
  quickAddChapters,
  clearBatchRows,
  importFromBulkText,
  removeBatchRow,
  submitChapter,
  submitBatch,
  fillBatchFromAI,
} = useDashboardBatchDialog({ outline, outlineTheme, form })

const activeTab = ref('workbench')
const { restartDashboardTimer, stopDashboardPolling, tasksStore } = useDashboardPolling({
  activeTab,
  loadSerialData,
})

const { busy: autoRunBusy, dialogVisible: autoRunDialogVisible } = useNovelBatchRun()

watch(autoRunBusy, async (now, prev) => {
  if (prev && !now && !autoRunDialogVisible.value) {
    await loadWorkbench(loadSerialData)
  }
})

onMounted(async () => {
  await loadWorkbench(loadSerialData)
  restartDashboardTimer()
  watch(() => tasksStore.isRunning, restartDashboardTimer)
  tasksStore.startPolling()
})

onUnmounted(() => {
  stopDashboardPolling()
  tasksStore.stopPolling()
})
</script>

<template>
  <section class="dashboard">
    <header class="page-head">
      <div>
        <h1>工作台</h1>
        <p>触发章节生成、查看产出与长篇指标。</p>
      </div>
      <div class="head-actions">
        <el-button :icon="DocumentAdd" @click="router.push('/outline')">查看大纲</el-button>
        <el-button type="primary" :icon="Plus" :disabled="tasksStore.isRunning" @click="openAddChapterDialog">
          运行单章
        </el-button>
      </div>
    </header>

    <el-tabs v-model="activeTab" class="dashboard-main-tabs">
      <!-- Tab 1: 创作工作台 -->
      <el-tab-pane label="创作工作台" name="workbench" class="tab-pane-workbench">
        <div class="workbench-pane">
          <DashboardStats class="workbench-stats workbench-stats-top" />

          <ProjectReadinessCard
            :engine-ready="engineStatus.ready"
            :outline="outline"
            :assets="assets"
            :max-available-chapters="maxAvailableChapters"
            :semantic-search-effective="semanticSearchEffective"
            :vector-enabled="vectorEnabledForProject"
            :work-scale="workScale"
          />

          <AgentProductionLine
            :engine-ready="engineStatus.ready"
            :outline="outline"
            :assets="assets"
            :max-available-chapters="maxAvailableChapters"
            :semantic-search-effective="semanticSearchEffective"
            :vector-enabled="vectorEnabledForProject"
            :work-scale="workScale"
            show-controls
          />

          <ScaleArchitecturePanel
            :outline="outline"
            :scale-profile="scaleProfile"
            :chapters-written="chapterCountTotal"
            @saved="refreshScaleArchitecture"
          />
        </div>
      </el-tab-pane>

      <!-- Tab 2: 长篇指标 -->
      <el-tab-pane label="长篇指标" name="metrics" class="tab-pane-metrics">
        <div class="workbench-pane">
          <div class="workbench-metrics" style="padding-top: 16px;">
            <div class="control-section-head control-section-compact">
              <h2 class="control-section-title">长篇指标（只读）</h2>
              <p class="control-section-hint">
                体量请改
                <el-button type="primary" link @click="activeTab = 'workbench'">工作台 · 体量架构</el-button>
                · 连载进阶见
                <el-button type="primary" link @click="activeTab = 'serialization'">连载运营</el-button>
              </p>
            </div>
            <div class="control-grid control-grid-compact">
              <section class="panel report-panel">
                <div class="panel-header panel-header-compact">
                  <div class="panel-header-left">
                    <el-icon class="panel-icon report-color"><Warning /></el-icon>
                    <h2>校准报告</h2>
                  </div>
                </div>
                <div class="panel-body-scroll">
                  <div v-if="calibration.issues?.length" class="issue-list">
                    <p v-for="issue in calibration.issues" :key="issue">
                      <el-icon><WarningFilled /></el-icon>{{ issue }}
                    </p>
                  </div>
                  <el-empty v-else description="指标正常" :image-size="56" />
                </div>
              </section>

              <section class="panel pace-panel">
                <div class="panel-header panel-header-compact">
                  <div class="panel-header-left">
                    <el-icon class="panel-icon pace-color"><Timer /></el-icon>
                    <h2>节奏比例</h2>
                  </div>
                </div>
                <div class="pace-grid pace-grid-compact">
                  <div>
                    <strong>{{ calibration.pacing?.counts?.setup || 0 }}</strong>
                    <span>铺垫</span>
                  </div>
                  <div>
                    <strong>{{ calibration.pacing?.counts?.build || 0 }}</strong>
                    <span>蓄力</span>
                  </div>
                  <div>
                    <strong>{{ calibration.pacing?.counts?.burst || 0 }}</strong>
                    <span>爆发</span>
                  </div>
                  <div>
                    <strong>{{ calibration.pacing?.counts?.transition || 0 }}</strong>
                    <span>过渡</span>
                  </div>
                </div>
                <p v-for="issue in calibration.pacing?.issues || []" :key="issue" class="muted-line muted-line-compact">{{ issue }}</p>
              </section>

              <section class="panel debt-panel full-row">
                <div class="panel-header panel-header-compact">
                  <div class="panel-header-left">
                    <el-icon class="panel-icon debt-color"><WarningFilled /></el-icon>
                    <h2>叙事债务</h2>
                  </div>
                </div>
                <div class="panel-body-scroll debt-scroll">
                  <div v-if="allDebt.length" class="debt-list debt-list-compact">
                    <article v-for="item in allDebt.slice(0, 8)" :key="`${item.kind}-${item.id}`" :class="['debt-row', item.debt_status]">
                      <el-tag :type="item.kind === '伏笔' ? 'danger' : item.kind === '秘密' ? 'warning' : 'info'" size="small">{{ item.kind }}</el-tag>
                      <strong>{{ item.title || item.id }}</strong>
                      <span class="debt-desc">{{ item.description }}</span>
                      <small>第 {{ item.chapter_id }} 章 · {{ item.debt_status || 'open' }}</small>
                    </article>
                  </div>
                  <el-empty v-else description="暂无债务" :image-size="56" />
                </div>
              </section>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- Tab 3: 连载主控中心 -->
      <el-tab-pane label="连载运营（高级）" name="serialization" class="tab-pane-serialization">
        <el-alert
          type="info"
          :closable="false"
          show-icon
          class="serial-advanced-hint"
          title="日常写书可忽略本页"
          description="纠偏大纲、叙事债、连载导出等进阶能力；日常只需「创作工作台」+ 章节维护。"
        />
        <!-- 连载大盘数据快报 -->
        <section class="serial-overview-cards">
          <div class="serial-stat-card">
            <span class="stat-label">今日连载字数</span>
            <strong class="stat-val text-primary">{{ serialStatus.today_word_count }}</strong>
            <span class="stat-tip">今日更新的汉字总数</span>
          </div>
          <div class="serial-stat-card">
            <span class="stat-label">全书批量已完成（权威）</span>
            <strong class="stat-val text-info">{{ serialStatus.authoritative_completed }} <small>章</small></strong>
            <span class="stat-tip">与大纲页进度摘要 novel_batch_progress 一致</span>
          </div>
          <div class="serial-stat-card">
            <span class="stat-label">磁盘有正文 / 书库索引</span>
            <strong class="stat-val">{{ serialStatus.disk_chapters_with_final }} / {{ serialStatus.library_indexed }}</strong>
            <span class="stat-tip">正文目录数 · SQLite 章数（参考）</span>
          </div>
          <div class="serial-stat-card">
            <span class="stat-label">待审批设定变更</span>
            <strong class="stat-val" :class="serialStatus.pending_candidates_count > 0 ? 'text-warning' : 'text-success'">
              {{ serialStatus.pending_candidates_count }} <small>个</small>
            </strong>
            <span class="stat-tip">暂存状态的 Pending Candidate</span>
          </div>
          <div class="serial-stat-card">
            <span class="stat-label">读者流失指标</span>
            <strong class="stat-val" :class="serialStatus.crisis_level === '正常' ? 'text-success' : serialStatus.crisis_level === '中度警戒' ? 'text-warning' : 'text-danger'">
              {{ (serialStatus.avg_bounce_rate * 100).toFixed(1) }}%
            </strong>
            <span class="stat-badge" :class="serialStatus.crisis_level === '正常' ? 'badge-success' : serialStatus.crisis_level === '中度警戒' ? 'badge-warning' : 'badge-danger'">
              {{ serialStatus.crisis_level }}
            </span>
          </div>
        </section>

        <!-- 危机预警与一键纠偏 -->
        <section v-if="serialStatus.crisis_level !== '正常'" class="crisis-alert-banner">
          <div class="alert-left">
            <el-icon class="alert-icon pulse"><Warning /></el-icon>
            <div class="alert-text">
              <h3>【大纲自适应纠偏警告】：读者流失过高！</h3>
              <p>当前读者流失表现为 <strong>{{ serialStatus.crisis_level }}</strong>。反馈指出节奏拖沓、爽点匮乏。建议立刻让 AI 主编根据读者吐槽对后续章节大纲进行自适应纠偏！</p>
            </div>
          </div>
          <el-button type="danger" :loading="rewritingOutline" :disabled="tasksStore.isRunning || rewritingOutline" @click="triggerAdaptiveRewrite">一键大纲纠偏</el-button>
        </section>

        <!-- 连载工作区双栏布局 -->
        <div class="serial-workspace">
          <!-- 左栏：读者模拟评论书评区 -->
          <article class="serial-column comment-area">
            <div class="column-header">
              <h3><el-icon><ChatLineRound /></el-icon> 读者模拟评论区</h3>
              <el-button size="small" :icon="Refresh" @click="loadSerialData">刷新评论</el-button>
            </div>
            
            <div class="comments-list-wrapper">
              <div v-if="virtualComments.length === 0" class="empty-placeholder">
                <p>暂无读者评论。请先生成章节，系统将根据跳出率模拟真实书评吐槽。</p>
              </div>
              <div v-else class="comments-scroll-list">
                <div v-for="c in virtualComments" :key="c.id" class="comment-card">
                  <div class="comment-card-head">
                     <img :src="c.avatar || 'https://cube.elemecdn.com/3/7c/3ea6beec64369c2642b92c6726f1epng.png'" class="comment-avatar" alt="avatar" />
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

          <!-- 右栏：自动同步设定状态 -->
          <article class="serial-column pending-states-area">
            <div class="column-header" style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
              <h3 style="display: flex; align-items: center; gap: 6px;"><el-icon><Check /></el-icon> 设定自动同步</h3>
              <div style="display: flex; align-items: center; gap: 8px;">
                <span class="badge">默认自动通过</span>
              </div>
            </div>

            <div class="states-list-wrapper">
              <div class="empty-placeholder">
                <el-icon class="success-icon"><Check /></el-icon>
                <p>当前实体设定会在生成完成后自动通过并同步，无需人工审批。</p>
              </div>
            </div>
          </article>
        </div>

        <!-- 底部打包连载包导出 -->
        <section class="serial-export-footer">
          <div class="export-text">
            <h3>一键导出已更新连载包</h3>
            <p>导出所有已物理生成的正式章节正文，打包为压缩包(ZIP)或合并为单文本(TXT)。</p>
          </div>
          <div class="export-actions">
            <el-button type="warning" plain :loading="copyingTrial" @click="copyTrialForPlatform">
              复制试发（剪贴板）
            </el-button>
            <el-button type="success" :icon="Download" :loading="exportingSerial" @click="downloadSerial('txt')">缝合单文本 (TXT)</el-button>
            <el-button type="primary" :icon="Download" :loading="exportingSerial" @click="downloadSerial('zip')">打包分章压缩包 (ZIP)</el-button>
          </div>
          <p v-if="serialStatus.progress_note" class="serial-progress-note">{{ serialStatus.progress_note }}</p>
        </section>
      </el-tab-pane>


    </el-tabs>

    <!-- 智能纠偏大纲对比 Dialog -->
    <el-dialog v-model="outlineDiffDialogVisible" title="大纲自适应纠偏对比" width="850px" top="8vh" destroy-on-close>
      <div class="outline-diff-container">
        <div class="diff-header-info">
          <el-icon class="warning-icon"><Warning /></el-icon>
          <div>
            <h4>主编整改指令已生成</h4>
            <p>已针对当前异常跳出率对后续 3 章大纲进行重写，压缩日常并提升核心戏剧冲突。请对比并决定是否应用：</p>
          </div>
        </div>

        <div class="diff-columns">
          <div class="diff-col old-chapters-col">
            <h3>原定大纲走向</h3>
            <div class="diff-chapters-scroll">
              <div v-for="ch in adaptiveOutlineDiff.old_chapters" :key="ch.chapter_id" class="diff-chapter-card">
                <div class="ch-title">第 {{ ch.chapter_id }} 章：{{ ch.title || ch.chapter_title }}</div>
                <div class="ch-content">{{ ch.goal || ch.detailed_synopsis }}</div>
              </div>
            </div>
          </div>

          <div class="diff-col new-chapters-col">
            <h3>纠偏后走向（加速爽点爆发）</h3>
            <div class="diff-chapters-scroll">
              <div v-for="ch in adaptiveOutlineDiff.new_chapters" :key="ch.chapter_id" class="diff-chapter-card highlight-card">
                <div class="ch-title">第 {{ ch.chapter_id }} 章：{{ ch.chapter_title || ch.title }}</div>
                <div class="ch-content">{{ ch.detailed_synopsis || ch.goal }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="outlineDiffDialogVisible = false">取消</el-button>
        <el-button type="danger" :loading="applyingOutline" @click="applyAdaptive">确认应用纠偏大纲</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="addChapterDialogVisible" title="高级 · 补跑单章 / 列表" width="780px" top="6vh" destroy-on-close>
      <el-alert type="info" :closable="false" show-icon class="gen-mode-alert">
        <template #title>和「连写启动」的区别</template>
        <p class="gen-mode-text">
          <strong>连写启动</strong>（主按钮）：走卷队列 autopilot，长篇按卷滚动，适合连续写书。
          <strong>写作页 → AI 写作</strong>：边改边跑当前章流水线（常用）；会覆盖本章正文前会先提示。
          <strong>本对话框 · 单章</strong>：不打开写作页也可提交；<strong>列表</strong>：批量填 ID+目标，均不走全书规划。
        </p>
      </el-alert>
      <el-tabs v-model="addChapterTab" class="add-chapter-tabs">
        <el-tab-pane label="单章（不打开写作页）" name="single">
          <div class="run-form" style="display: grid; gap: 14px; margin-top: 10px;">
            <label style="display: grid; gap: 6px;">
              <span style="font-size: 13.5px; font-weight: 700; color: var(--color-text-muted);">章节编号</span>
              <el-input v-model="form.chapter_id" placeholder="001" style="width: 120px;" />
            </label>
            <label style="display: grid; gap: 6px;">
              <span style="font-size: 13.5px; font-weight: 700; color: var(--color-text-muted);">章节目标</span>
              <el-input
                v-model="form.goal"
                type="textarea"
                :rows="6"
                resize="none"
                placeholder="描述本章要推进的事件、冲突、伏笔或人物变化"
              />
            </label>
          </div>
          <div class="dialog-footer-actions" style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px;">
            <el-button @click="addChapterDialogVisible = false">取消</el-button>
            <el-button type="primary" :loading="loading" :disabled="tasksStore.isRunning || loading" @click="submitChapter">运行章节流水线</el-button>
          </div>
        </el-tab-pane>

        <el-tab-pane label="指定列表（无全书规划）" name="batch">
          <div class="batch-mode-selector" style="margin: 10px 0 16px; display: flex; justify-content: center;">
            <el-radio-group v-model="batchInputMode" size="small">
              <el-radio-button value="list">列表录入</el-radio-button>
              <el-radio-button value="bulk">文本批量导入</el-radio-button>
            </el-radio-group>
          </div>

          <div v-if="batchInputMode === 'list'" class="list-mode-content">
            <div class="batch-toolbar">
              <div class="toolbar-left">
                <el-button type="primary" :loading="chapterPlanGenerating" :disabled="tasksStore.isRunning || chapterPlanGenerating" @click="fillBatchFromAI">AI 根据大纲拆章</el-button>
                <el-button text :icon="Plus" :disabled="tasksStore.isRunning" @click="addBatchRow">添加一行</el-button>
                <el-button text :disabled="tasksStore.isRunning" @click="quickAddChapters(5)">+ 快速加 5 章</el-button>
                <el-button text :disabled="tasksStore.isRunning" @click="quickAddChapters(10)">+ 快速加 10 章</el-button>
              </div>
              <el-button text type="danger" :disabled="tasksStore.isRunning" @click="clearBatchRows">一键清空</el-button>
            </div>
            <div class="ai-plan-options">
              <span>生成</span>
              <el-input-number v-model="chapterPlanCount" :min="1" :max="200" size="small" />
              <span>章</span>
              <el-input v-model="chapterPlanInstructions" size="small" placeholder="可选：本轮拆章重点，例如先打进城市赛" />
            </div>

            <div class="batch-list" style="margin-top: 14px; max-height: 380px; overflow-y: auto; display: grid; gap: 8px;">
              <div v-for="(row, index) in batchRows" :key="index" class="batch-row">
                <el-input v-model="row.chapter_id" placeholder="编号" class="batch-id" />
                <el-input v-model="row.goal" placeholder="章节目标描述" />
                <el-button text type="danger" :icon="Delete" :disabled="batchRows.length <= 1" @click="removeBatchRow(index)" />
              </div>
            </div>
          </div>

          <div v-else class="bulk-mode-content" style="margin-top: 10px;">
            <p class="bulk-tip">请输入多个章节的目标描述，每一行代表一个章节：</p>
            <el-input
              v-model="bulkText"
              type="textarea"
              :rows="10"
              placeholder="例如：&#10;第一章：主角在雨夜回家的路上，遭遇了诡异车祸……&#10;第二章：在白塔医院醒来，却发现自己意外获得了透视眼……&#10;第三章：出院回家，遇到恶毒房东催租，发生冲突……"
              class="bulk-textarea"
            />
            <div class="bulk-actions" style="margin-top: 10px; display: flex; justify-content: flex-end;">
              <el-button type="primary" @click="importFromBulkText">解析并导入到列表</el-button>
            </div>
          </div>

          <div class="dialog-footer-actions" style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px;">
            <el-button @click="addChapterDialogVisible = false">取消</el-button>
            <el-button type="primary" :loading="batchSubmitting" :disabled="tasksStore.isRunning || batchSubmitting" @click="submitBatch">
              提交批量任务 (共 {{ batchRows.filter((row) => row.chapter_id.trim() && row.goal.trim()).length }} 章)
            </el-button>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>

    <NovelBatchRunDialog />

  </section>
</template>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
}

.serial-advanced-hint {
  margin-bottom: 14px;
}

.dropdown-caret {
  margin-left: 4px;
  font-size: 10px;
}

.dashboard-main-tabs {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.dashboard-main-tabs :deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.dashboard-main-tabs :deep(.el-tab-pane) {
  height: 100%;
}

.dashboard-main-tabs :deep(.tab-pane-workbench) {
  overflow-x: hidden;
  overflow-y: auto;
  padding-right: 4px;
  padding-bottom: 36px;
  scroll-padding-bottom: 28px;
}

.dashboard-main-tabs :deep(.tab-pane-serialization) {
  overflow-x: hidden;
  overflow-y: auto;
  padding-right: 4px;
  padding-bottom: 40px;
  scroll-padding-bottom: 32px;
}

.workbench-pane {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: min-content;
  padding-bottom: 8px;
}



.workbench-stats {
  flex-shrink: 0;
}

.workbench-main-grid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr);
  gap: 10px;
  overflow: hidden;
}

.workbench-main-grid-single {
  grid-template-columns: minmax(0, 1fr);
  flex: 0 1 auto;
  min-height: 220px;
  max-height: min(52vh, 520px);
}

.workbench-metrics-collapse {
  flex-shrink: 0;
  border: none;
  background: transparent;
}

.workbench-metrics-collapse :deep(.el-collapse-item__header) {
  font-size: 14px;
  font-weight: 700;
  color: var(--color-text);
  height: 40px;
  border-bottom: 1px solid var(--color-bg-hover);
}

.workbench-metrics-collapse :deep(.el-collapse-item__content) {
  padding-bottom: 0;
}

.workbench-metrics {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow: hidden;
}

.pipeline-compact .section-head-compact {
  padding: 10px 14px;
}

.pipeline-compact .section-head-compact h2 {
  font-size: 15px;
}

.pipeline-compact .stage-card {
  padding: 10px 12px;
  gap: 4px;
}

.pipeline-compact .stage-card strong {
  font-size: 13px;
}

.pipeline-compact .stage-card p {
  font-size: 12.5px;
  -webkit-line-clamp: 2;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.head-actions,
.outline-actions,
.engine-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.top-grid,
.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(340px, 0.75fr);
  gap: 20px;
}

.run-panel,
.asset-panel,
.outline-panel,
.pipeline-panel {
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: var(--color-bg-surface);
  box-shadow: 0 10px 30px -10px rgba(15, 23, 42, 0.04), 
              0 1px 3px rgba(15, 23, 42, 0.02);
  transition: box-shadow 0.3s;
}

.run-panel:hover,
.asset-panel:hover,
.pipeline-panel:hover {
  box-shadow: 0 12px 36px -8px rgba(15, 23, 42, 0.07), 
              0 2px 4px rgba(15, 23, 42, 0.02);
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-bg-hover);
}

.section-head h2 {
  margin: 0;
  color: var(--color-text-strong);
  font-size: 17px;
  font-weight: 800;
}

.hint {
  color: var(--color-text-muted);
  font-size: 13px;
  font-weight: normal;
}

.run-form,
.dialog-form {
  display: grid;
  gap: 14px;
  padding: 20px;
}

.run-form label,
.dialog-form label {
  display: grid;
  gap: 6px;
}

.run-form span,
.dialog-form span {
  color: var(--color-text);
  font-size: 13px;
  font-weight: 700;
}

.stage-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  border-top: 1px solid var(--color-border-subtle);
}

.stage-card {
  min-width: 0;
  display: grid;
  align-content: start;
  gap: 8px;
  padding: 14px;
  border-right: 1px solid var(--color-border-subtle);
}

.stage-card:last-child {
  border-right: 0;
}

.stage-card span {
  color: #c66f4f;
  font-size: 12px;
  font-weight: 800;
}

.stage-card strong {
  color: var(--color-text-strong);
  font-size: 15px;
  line-height: 1.35;
}

.stage-card p {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.45;
}

.batch-mode-selector {
  margin-bottom: 16px;
  display: flex;
  justify-content: center;
}

.list-mode-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.batch-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--color-bg-surface-muted);
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid var(--color-border);
  margin-bottom: 8px;
}

.toolbar-left {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.ai-plan-options {
  display: grid;
  grid-template-columns: auto 120px auto minmax(220px, 1fr);
  align-items: center;
  gap: 8px;
  color: var(--color-text-muted);
  font-size: 13px;
}

.bulk-mode-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.bulk-tip {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-muted);
}

.bulk-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 6px;
}

.batch-row {
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr) 42px;
  gap: 8px;
  align-items: center;
}

@media (max-width: 1120px) {
  .page-head {
    align-items: stretch;
    flex-direction: column;
    gap: 12px;
  }

  .top-grid,
  .dashboard-grid {
    grid-template-columns: 1fr;
  }

  .stage-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .stage-card {
    border-bottom: 1px solid var(--color-border-subtle);
  }
}

/* ---- Serialization Workspace Modern CSS ---- */
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

.badge-success { background: #ecfdf5; color: var(--color-success); }
.badge-warning { background: #fffbeb; color: var(--color-warning); }
.badge-danger { background: #fef2f2; color: var(--color-danger); }

.text-primary { color: var(--color-primary) !important; }
.text-info { color: #06b6d4 !important; }
.text-success { color: var(--color-success) !important; }
.text-warning { color: var(--color-warning) !important; }
.text-danger { color: var(--color-danger) !important; }

/* 危机警报条 */
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
  0% { transform: scale(1); }
  50% { transform: scale(1.15); opacity: 0.8; }
  100% { transform: scale(1); }
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

/* 左右双栏 */
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

.column-header h3 {
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

/* 评论卡片 */
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

/* 设定审批卡片 */
.candidates-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.candidate-card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-subtle);
  border-radius: 10px;
  padding: 14px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.01);
}

.candidate-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 10px;
  border-bottom: 1px dashed var(--color-border);
  margin-bottom: 10px;
}

.candidate-chapter {
  font-size: 12px;
  font-weight: 700;
  background: var(--color-bg-hover);
  color: var(--color-text-muted);
  padding: 2px 6px;
  border-radius: 4px;
}

.candidate-entity {
  font-size: 13px;
  font-weight: 800;
  color: var(--color-text-strong);
}

.candidate-change-diff {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.diff-field {
  font-size: 12px;
}

.diff-label {
  color: var(--color-text-muted);
}

.diff-field code {
  background: var(--color-bg-surface-muted);
  color: var(--color-text-strong);
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 700;
}

.diff-val-box {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 4px;
}

.diff-val {
  padding: 8px;
  border-radius: 6px;
  font-size: 12.5px;
  line-height: 1.4;
  min-height: 50px;
}

.diff-val p {
  margin: 4px 0 0;
  font-weight: 550;
  word-break: break-all;
}

.val-title {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  display: block;
}

.old-val {
  background: #fff5f5;
  border: 1px solid #fee2e2;
  color: #c53030;
}

.old-val .val-title {
  color: var(--color-danger);
}

.new-val {
  background: #f0fdf4;
  border: 1px solid #dcfce7;
  color: #15803d;
}

.new-val .val-title {
  color: var(--color-success);
}

.change-reason {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--color-text-muted);
  line-height: 1.4;
}

.candidate-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 12px;
  border-top: 1px solid var(--color-bg-hover);
  padding-top: 10px;
}

/* 底部导出条 */
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

/* 大纲纠偏对比容器 */
.outline-diff-container {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.diff-header-info {
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 8px;
  padding: 12px 16px;
  display: flex;
  gap: 12px;
  align-items: center;
}

.warning-icon {
  font-size: 26px;
  color: var(--color-warning);
}

.diff-header-info h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 800;
  color: #92400e;
}

.diff-header-info p {
  margin: 2px 0 0;
  font-size: 12.5px;
  color: #b45309;
}

.diff-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.diff-col {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
  background: var(--color-bg-surface);
}

.diff-col h3 {
  margin: 0;
  background: var(--color-bg-surface-muted);
  padding: 10px 14px;
  font-size: 13.5px;
  font-weight: 800;
  color: var(--color-text);
  border-bottom: 1px solid var(--color-border);
}

.diff-chapters-scroll {
  height: 380px;
  overflow-y: auto;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: var(--color-bg-surface-muted);
}

.diff-chapter-card {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 10px;
  font-size: 12.5px;
}

.diff-chapter-card .ch-title {
  font-weight: 800;
  color: var(--color-text-strong);
  margin-bottom: 4px;
}

.diff-chapter-card .ch-content {
  color: var(--color-text-muted);
  line-height: 1.4;
}

.highlight-card {
  border-color: #bbf7d0;
  background: #f0fdf4;
}

.highlight-card .ch-title {
  color: #15803d;
}

.highlight-card .ch-content {
  color: #166534;
}

.control-section-head {
  margin-bottom: 10px;
}

.control-section-title {
  margin: 0;
  font-size: 17px;
  color: var(--color-text-strong);
}

.control-section-hint {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--color-text-muted);
}

.gen-mode-alert {
  margin-bottom: 14px;
}

.gen-mode-text {
  margin: 6px 0 0;
  font-size: 13px;
  line-height: 1.55;
  color: var(--color-text-muted);
}

/* 长篇控制并在工作台新增样式 */
.status-strip {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.status-item {
  border: 1px solid var(--color-border);
  background: var(--color-bg-surface);
  border-radius: 10px;
  padding: 14px 16px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}

.status-item strong {
  display: block;
  font-size: 24px;
  color: var(--color-text-strong);
}

.status-item span {
  color: var(--color-text-muted);
  font-size: 13px;
}

.status-item.ok strong {
  color: #1c7c54;
}

.status-item.warn strong {
  color: #c66f4b;
}

.control-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.control-grid-compact {
  flex: 1;
  min-height: 0;
  gap: 10px;
  grid-template-rows: minmax(0, 1fr) minmax(0, 1.15fr);
}

.control-grid .panel {
  border: 1px solid var(--color-border);
  background: var(--color-bg-surface);
  border-radius: 10px;
  padding: 18px;
  min-height: 240px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
}

.control-grid-compact .panel {
  min-height: 0;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
}

.panel-header-compact {
  margin-bottom: 8px !important;
}

.panel-header-compact h2 {
  font-size: 14px !important;
}

.panel-body-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.control-section-compact .control-section-title {
  font-size: 14px;
}

.control-section-compact .control-section-hint {
  margin-top: 2px;
  font-size: 12px;
}

.pace-grid-compact {
  gap: 8px;
}

.pace-grid-compact strong {
  font-size: 20px;
}

.muted-line-compact {
  font-size: 11px;
  margin: 4px 0 0;
}

.debt-list-compact .debt-row {
  padding: 8px 10px;
  gap: 4px;
}

.debt-list-compact .debt-desc {
  font-size: 12px;
  -webkit-line-clamp: 1;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.workbench-stats :deep(.metric-grid) {
  gap: 10px;
}

.workbench-stats :deep(.metric) {
  min-height: 68px;
  padding: 10px 12px;
}

.workbench-stats :deep(.metric-icon) {
  width: 40px;
  height: 40px;
  font-size: 18px;
}

.workbench-stats :deep(.metric-value) {
  font-size: 22px;
  margin-top: 4px;
}

.workbench-stats :deep(.metric-label) {
  font-size: 12px;
}

@media (max-width: 1200px) {
  .workbench-main-grid {
    grid-template-columns: 1fr;
    grid-template-rows: minmax(180px, 0.45fr) minmax(0, 1fr);
  }
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  width: 100%;
}

.panel-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-header-left h2 {
  margin: 0 !important;
  font-size: 18px;
  color: var(--color-text-strong);
  font-weight: 750;
}

.panel-icon {
  font-size: 18px;
  padding: 6px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.scale-color {
  color: var(--color-primary);
  background: var(--color-primary-soft);
}

.genes-color {
  color: #8b5cf6;
  background: #f5f3ff;
}

.report-color {
  color: var(--color-warning);
  background: #fef9c3;
}

.pace-color {
  color: var(--color-success);
  background: #ecfdf5;
}

.debt-color {
  color: var(--color-danger);
  background: #fef2f2;
}

.genes-panel dl,
.scale-panel dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 0 0 14px;
}

.genes-panel dt,
.scale-panel dt {
  color: var(--color-text-muted);
  font-size: 12px;
}

.genes-panel dd,
.scale-panel dd {
  margin: 4px 0 0;
  font-weight: 700;
  color: var(--color-text-strong);
}

.guard-list-container {
  margin-top: 10px;
  border-top: 1px dashed var(--color-border);
  padding-top: 10px;
}

.guard-title {
  display: block;
  font-size: 12px;
  color: var(--color-text-muted);
  margin-bottom: 6px;
}

.guard-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.guard-list span {
  border: 1px solid #f0c9b7;
  background: #fff3ed;
  color: #9a5033;
  border-radius: 999px;
  padding: 5px 9px;
  font-size: 12px;
}

.issue-list p {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 10px;
  color: #9a5033;
}

.pace-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}

.pace-grid div {
  background: var(--color-bg-surface-muted);
  border-radius: 8px;
  padding: 14px 10px;
  text-align: center;
  border: 1px solid var(--color-border-subtle);
}

.pace-grid strong {
  display: block;
  font-size: 24px;
  color: var(--color-text-strong);
}

.pace-grid span,
.muted-line {
  color: var(--color-text-muted);
  font-size: 13px;
}

.warn-text {
  color: #c66f4b !important;
  font-weight: bold;
}

.full-row {
  grid-column: 1 / -1;
}

.debt-list {
  display: grid;
  gap: 8px;
}

.debt-row {
  display: grid;
  grid-template-columns: 80px 200px 1fr 260px;
  gap: 12px;
  align-items: center;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 10px 12px;
}

.debt-row.overdue {
  border-color: #f0b7a2;
  background: #fff5f0;
}

.debt-row.due_soon {
  border-color: #f2d38c;
  background: #fffbef;
}

.debt-desc {
  font-size: 13px;
  color: var(--color-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
}

.debt-row span,
.debt-row small {
  color: var(--color-text-muted);
  font-size: 12px;
}

.debt-row strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 980px) {
  .status-strip,
  .control-grid,
  .genes-panel dl,
  .scale-panel dl {
    grid-template-columns: 1fr;
  }

  .debt-row {
    grid-template-columns: 1fr;
  }
}

.workbench-stats-top {
  margin-bottom: 16px;
}

.workbench-pane > :deep(.readiness-row),
.workbench-pane > :deep(.production-line) {
  margin-bottom: 16px;
}
</style>
