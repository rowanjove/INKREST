<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { ElMessage } from 'element-plus'
import {
  ArrowLeft, Calendar, CircleCheck, Compass, CopyDocument, Document,
  InfoFilled, Location, RefreshRight, SuccessFilled, Warning,
  Edit
} from '@element-plus/icons-vue'
import { copyChapterPlainText } from '../utils/copyChapterText'
import { useChapterStore } from '../stores/chapter'
import {
  rerunChapterGate,
  resumeChapterAudit,
  rewriteChapter,
  setChapterExternalReview,
  updateChapter,
} from '../api'
import { DUAL_AUDIT_HINT } from '../constants/repairWorkflow'
import ChapterContent from '../components/ChapterContent.vue'
import ChapterPlan from '../components/ChapterPlan.vue'
import ChapterAudit from '../components/ChapterAudit.vue'
import ChapterQualityReport from '../components/ChapterQualityReport.vue'
import ChapterUnifiedGate from '../components/ChapterUnifiedGate.vue'

const route = useRoute()
const router = useRouter()
const chapterStore = useChapterStore()
const { currentChapter: chapter } = storeToRefs(chapterStore)
const activeTab = ref('final')
const loadError = ref('')
const rewriting = ref(false)
const resumingAudit = ref(false)
const rerunningGate = ref(false)
const externalStatus = ref<'none' | 'pending_external' | 'external_passed'>('none')
const copying = ref(false)
const editDialogVisible = ref(false)
const savingEdit = ref(false)
const editForm = ref({
  title: '',
  final_text: '',
})
const hasFinalText = computed(() => Boolean(chapter.value?.final_text?.trim()))

const startEdit = () => {
  if (!chapter.value) return
  editForm.value.title = chapter.value.title || ''
  editForm.value.final_text = chapter.value.final_text || ''
  editDialogVisible.value = true
}

const handleSaveEdit = async () => {
  if (!chapter.value?.chapter_id) return
  savingEdit.value = true
  try {
    await updateChapter(chapter.value.chapter_id, {
      title: editForm.value.title,
      final_text: editForm.value.final_text,
    })
    ElMessage.success('保存章节修改成功')
    editDialogVisible.value = false
    await chapterStore.fetchChapter(chapter.value.chapter_id)
  } catch (error: any) {
    ElMessage.error(error.message || '保存章节修改失败')
  } finally {
    savingEdit.value = false
  }
}

onMounted(async () => {
  const tab = route.query.tab
  if (typeof tab === 'string' && tab) {
    activeTab.value = tab === 'gate' ? 'unified_gate' : tab
  }
  try {
    await chapterStore.fetchChapter(route.params.id as string)
    const ext = (chapterStore.currentChapter as { external_review_status?: string } | null)
      ?.external_review_status
    if (ext === 'pending_external' || ext === 'external_passed') {
      externalStatus.value = ext
    } else {
      externalStatus.value = 'none'
    }
  } catch (error: any) {
    loadError.value = error.message || '章节加载失败'
  }
})

const parseMarkdown = (md: string) => {
  if (!md) return ''
  let html = md.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  const lines = html.split('\n')
  const result: string[] = []
  let inList = false
  for (const line of lines) {
    const trimmed = line.trim()
    if (trimmed.startsWith('## ')) {
      if (inList) { result.push('</ul>'); inList = false }
      result.push(`<h3 class="md-h3">${trimmed.substring(3)}</h3>`)
    } else if (trimmed.startsWith('# ')) {
      if (inList) { result.push('</ul>'); inList = false }
      result.push(`<h2 class="md-h2">${trimmed.substring(2)}</h2>`)
    } else if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      if (!inList) { result.push('<ul class="md-ul">'); inList = true }
      const itemText = trimmed.substring(2).replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      result.push(`<li class="md-li">${itemText}</li>`)
    } else if (trimmed === '') {
      if (inList) { result.push('</ul>'); inList = false }
    } else {
      if (inList) { result.push('</ul>'); inList = false }
      result.push(`<p class="md-p">${trimmed.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')}</p>`)
    }
  }
  if (inList) result.push('</ul>')
  return result.join('\n')
}

const hasStateUpdates = computed(() => {
  const su = chapter.value?.state_update
  if (!su) return false
  return (su.events?.length > 0) || (su.timeline_nodes?.length > 0) ||
    (su.timeline_edges?.length > 0) || (su.foreshadows?.length > 0) || (su.hooks?.length > 0)
})

const stateChangeCount = computed(() => {
  const su = chapter.value?.state_update
  if (!su) return 0
  return (su.events?.length || 0) + (su.timeline_nodes?.length || 0) + (su.foreshadows?.length || 0)
})

const isQualityBlocked = computed(() => {
  const cp = chapter.value?.checkpoint
  const gate = chapter.value?.unified_gate
  return cp?.last_stage === 'quality_blocked' || Boolean(gate?.blocked)
})

const resumableFrom = computed(() => {
  return (
    chapter.value?.checkpoint?.resumable_from ||
    chapter.value?.unified_gate?.resumable_from ||
    ''
  )
})

const wordStatusLabel = computed(() => {
  const count = chapter.value?.wordcount?.count || 0
  const status = chapter.value?.wordcount?.status
  if (!count || status === 'empty') return '空正文'
  if (status === 'under') return '字数不足'
  if (status === 'over') return '字数超出'
  if (status === 'ok') return '符合要求'
  return '未统计'
})

const handleCopyFullText = async () => {
  if (!chapter.value) return
  copying.value = true
  try {
    const len = await copyChapterPlainText({
      chapter_id: chapter.value.chapter_id,
      title: chapter.value.title,
      final_text: chapter.value.final_text,
    })
    ElMessage.success(`已复制全文（约 ${len} 字），可粘贴到网文平台`)
  } catch (error: any) {
    ElMessage.error(error?.message || '复制失败')
  } finally {
    copying.value = false
  }
}

const goWriter = () => {
  if (!chapter.value?.chapter_id) return
  router.push({ path: '/writer', query: { chapter: chapter.value.chapter_id } })
}

const handleRerunGate = async () => {
  if (!chapter.value?.chapter_id) return
  rerunningGate.value = true
  try {
    await rerunChapterGate(chapter.value.chapter_id)
    ElMessage.success('已提交只重跑门禁，请到章节维护查看')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error.message || '提交失败')
  } finally {
    rerunningGate.value = false
  }
}

const saveExternalStatus = async (status: 'none' | 'pending_external' | 'external_passed') => {
  if (!chapter.value?.chapter_id) return
  try {
    await setChapterExternalReview(chapter.value.chapter_id, { status })
    externalStatus.value = status
    ElMessage.success('外审状态已更新')
    await chapterStore.fetchChapter(chapter.value.chapter_id)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error.message || '保存失败')
  }
}

const handleResumeAudit = async () => {
  if (!chapter.value?.chapter_id) return
  resumingAudit.value = true
  try {
    await resumeChapterAudit(chapter.value.chapter_id)
    ElMessage.success('已提交重试审校，请到章节维护查看进度')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error.message || '提交失败')
  } finally {
    resumingAudit.value = false
  }
}

const openUnifiedGateTab = () => {
  activeTab.value = 'unified_gate'
}

const handleRewrite = async () => {
  if (!chapter.value?.chapter_id) return
  rewriting.value = true
  try {
    await rewriteChapter(chapter.value.chapter_id)
    ElMessage.success('重写任务已提交，可在日志中心查看任务流水')
  } catch (error: any) {
    ElMessage.error(error.message || '提交重写任务失败')
  } finally {
    rewriting.value = false
  }
}
</script>

<template>
  <el-alert v-if="loadError" :title="loadError" type="warning" show-icon style="margin-bottom: 24px" />

  <el-alert
    v-if="chapter"
    type="info"
    :closable="false"
    show-icon
    class="dual-audit-banner"
    title="两道审核说明"
    style="margin-bottom: 12px"
  >
    {{ DUAL_AUDIT_HINT }}
  </el-alert>

  <el-alert
    v-if="chapter && isQualityBlocked"
    type="error"
    :closable="false"
    show-icon
    title="本章处于质量阻断状态"
    style="margin-bottom: 16px"
  >
    终稿与审校报告仍在磁盘上，但状态落库未提交。
    <template v-if="resumableFrom">可从「{{ resumableFrom }}」阶段恢复流水线。</template>
    <div class="blocked-actions">
      <el-button type="warning" size="small" @click="goWriter">写作页改稿</el-button>
      <el-button
        type="primary"
        size="small"
        :loading="resumingAudit"
        @click="handleResumeAudit"
      >
        重试审校
      </el-button>
      <el-button
        size="small"
        plain
        :loading="rerunningGate"
        @click="handleRerunGate"
      >
        只重跑门禁
      </el-button>
      <el-button size="small" @click="openUnifiedGateTab">查看统一门禁</el-button>
      <el-button size="small" plain :loading="copying" @click="handleCopyFullText">
        复制全文试审
      </el-button>
    </div>
  </el-alert>

  <div v-if="chapter" class="chapter-detail-page">
    <div class="page-header-nav">
      <el-button @click="router.back()" class="back-btn" size="small">
        <el-icon><ArrowLeft /></el-icon> 返回
      </el-button>
      <div class="breadcrumbs">
        <span>章节列表</span> / <span class="active">章节详情</span>
      </div>
    </div>

    <div class="chapter-top-header">
      <div class="header-title-area">
        <span class="chapter-badge-id">CH {{ chapter.chapter_id }}</span>
        <h2 class="chapter-title-main" :title="chapter.title">{{ chapter.title || '无标题章节' }}</h2>
      </div>
      <div class="header-actions-area">
        <el-select
          v-model="externalStatus"
          size="default"
          class="external-select"
          placeholder="外审状态"
          @change="saveExternalStatus"
        >
          <el-option label="未标记" value="none" />
          <el-option label="待外审" value="pending_external" />
          <el-option label="外审已通过" value="external_passed" />
        </el-select>
        <el-button
          type="primary"
          plain
          :icon="CopyDocument"
          :loading="copying"
          @click="handleCopyFullText"
        >
          复制全文
        </el-button>
        <el-button
          v-if="hasFinalText"
          class="edit-btn"
          type="warning"
          :icon="Edit"
          @click="startEdit"
        >
          编辑本章
        </el-button>
        <el-tooltip
          v-if="hasFinalText"
          content="从规划阶段完整重跑流水线；质量阻断请用章节维护「重试审校」或本章「统一门禁」页。"
          placement="bottom"
        >
          <el-button
            class="rewrite-btn"
            type="primary"
            :icon="RefreshRight"
            :loading="rewriting"
            @click="handleRewrite"
          >
            整章重写
          </el-button>
        </el-tooltip>
      </div>
    </div>

    <el-row :gutter="16" class="meta-row">
      <el-col :span="8">
        <div class="meta-card">
          <div class="m-card-icon m-blue"><el-icon><Document /></el-icon></div>
          <div>
            <div class="m-val">{{ chapter.wordcount?.count || 0 }}</div>
            <div class="m-lbl">汉字字数</div>
          </div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="meta-card">
          <div class="m-card-icon m-orange"><el-icon><InfoFilled /></el-icon></div>
          <div>
            <div class="m-val">{{ wordStatusLabel }}</div>
            <div class="m-lbl">字数状态</div>
          </div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="meta-card">
          <div class="m-card-icon" :class="chapter.audit?.risk_level === '低' ? 'm-green' : 'm-red'"><el-icon><Warning /></el-icon></div>
          <div>
            <div class="m-val">{{ chapter.audit?.risk_level || '未审校' }}</div>
            <div class="m-lbl">安全风险等级</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <div class="detail-tabs-panel panel">
      <el-tabs v-model="activeTab" class="custom-detail-tabs">
        <el-tab-pane label="终稿正文" name="final">
          <ChapterContent
            :title="chapter.title"
            :chapter-id="chapter.chapter_id"
            :final-text="chapter.final_text"
          />
        </el-tab-pane>

        <el-tab-pane label="章节总结" name="summary">
          <div class="summary-container">
            <div class="md-preview" v-html="parseMarkdown(chapter.chapter_summary)"></div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="章节计划" name="plan">
          <ChapterPlan :plan="chapter.plan" />
        </el-tab-pane>

        <el-tab-pane label="安全审校" name="audit">
          <ChapterAudit :audit="chapter.audit" />
        </el-tab-pane>

        <el-tab-pane name="unified_gate">
          <template #label>
            <span>统一门禁</span>
            <el-badge v-if="isQualityBlocked" is-dot class="tab-badge-dot" />
          </template>
          <ChapterUnifiedGate
            :unified-gate="chapter.unified_gate || {}"
            :artifact-status="chapter.artifact_status || []"
          />
        </el-tab-pane>

        <el-tab-pane label="连续性检查" name="continuity">
          <div class="continuity-tab-content">
            <div class="audit-status-bar" :class="chapter.continuity?.pass ? 'risk-低' : 'risk-高'">
              <el-icon v-if="chapter.continuity?.pass"><CircleCheck /></el-icon>
              <el-icon v-else><Warning /></el-icon>
              <span>检查状态: <strong>{{ chapter.continuity?.pass ? '通过 (逻辑自洽)' : '未通过 (发现冲突设定)' }}</strong></span>
            </div>

            <div class="audit-issues-block">
              <h4 class="sub-section-title">逻辑一致性检查明细</h4>
              <div v-if="chapter.continuity?.issues?.length" class="issues-card-list">
                <div v-for="(issue, idx) in chapter.continuity.issues" :key="idx" class="issue-detail-card warning">
                  <span class="issue-badge">逻辑漏洞 #{{ Number(idx) + 1 }}</span>
                  <p class="issue-desc-text">{{ issue }}</p>
                </div>
              </div>
              <div v-else class="success-audit-state">
                <el-icon><SuccessFilled /></el-icon>
                <p>情节人物设定完全连贯，未发现时空冲突、道具丢失或角色前后行为逻辑相悖的问题。</p>
              </div>
            </div>

            <el-collapse class="raw-json-collapse">
              <el-collapse-item title="查看原始连续性检查 JSON 数据" name="raw">
                <pre class="raw-json-pre">{{ JSON.stringify(chapter.continuity, null, 2) }}</pre>
              </el-collapse-item>
            </el-collapse>
          </div>
        </el-tab-pane>

        <el-tab-pane label="质量报告" name="quality">
          <ChapterQualityReport :quality-report="chapter.quality_report || {}" />
        </el-tab-pane>

        <el-tab-pane label="设定同步状态" name="state_update">
          <div class="state-update-content">
            <div class="state-update-summary">
              本章共同步设定库变动:
              <strong>{{ stateChangeCount }}</strong> 项变更。
            </div>

            <div class="state-blocks-container" v-if="hasStateUpdates">
              <div class="state-block" v-if="chapter.state_update.events?.length">
                <h4 class="state-title-icon"><el-icon><Calendar /></el-icon> 新增历史大事件</h4>
                <div class="state-items">
                  <div v-for="evt in chapter.state_update.events" :key="evt.id" class="sub-state-item event">
                    <div class="sub-state-header">
                      <span class="s-id">{{ evt.id }}</span>
                      <span class="s-characters" v-if="evt.characters?.length">涉及角色: {{ evt.characters.join(', ') }}</span>
                    </div>
                    <p class="s-body">{{ evt.summary }}</p>
                  </div>
                </div>
              </div>

              <div class="state-block" v-if="chapter.state_update.timeline_nodes?.length">
                <h4 class="state-title-icon"><el-icon><Location /></el-icon> 实体与地点卡片更新</h4>
                <div class="state-items">
                  <div v-for="node in chapter.state_update.timeline_nodes" :key="node.id" class="sub-state-item node">
                    <div class="sub-state-header">
                      <span class="s-name">{{ node.name }}</span>
                      <span class="s-type">{{ node.type }}</span>
                    </div>
                    <p class="s-body">{{ node.description }}</p>
                  </div>
                </div>
              </div>

              <div class="state-block" v-if="chapter.state_update.foreshadows?.length">
                <h4 class="state-title-icon"><el-icon><Compass /></el-icon> 伏笔状态流</h4>
                <div class="state-items">
                  <div v-for="f in chapter.state_update.foreshadows" :key="f.id" class="sub-state-item foreshadow">
                    <div class="sub-state-header">
                      <span class="s-title">{{ f.title }}</span>
                      <span class="s-status" :class="f.status">{{ f.status === 'open' ? '未回收' : '已回收' }}</span>
                    </div>
                    <p class="s-body">{{ f.description }}</p>
                  </div>
                </div>
              </div>
            </div>

            <div v-else class="empty-state-card">
              <el-icon><InfoFilled /></el-icon>
              <p>本章写入没有引起小说背景库或全局设定库的状态变化。</p>
            </div>

            <el-collapse class="raw-json-collapse">
              <el-collapse-item title="查看原始状态更新 JSON 数据" name="raw">
                <pre class="raw-json-pre">{{ JSON.stringify(chapter.state_update, null, 2) }}</pre>
              </el-collapse-item>
            </el-collapse>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 编辑章节对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑章节"
      width="800px"
      destroy-on-close
      align-center
    >
      <el-form label-position="top">
        <el-form-item label="章节标题" required>
          <el-input v-model="editForm.title" placeholder="请输入章节标题" />
        </el-form-item>
        <el-form-item label="正文内容" required>
          <el-input
            v-model="editForm.final_text"
            type="textarea"
            :rows="18"
            placeholder="请输入正文内容..."
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="savingEdit" @click="handleSaveEdit">
            保存修改
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
  <el-skeleton v-else :rows="12" animated />
</template>

<style scoped>
.blocked-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.chapter-detail-page { display: flex; flex-direction: column; gap: 20px; }
.back-btn { border-radius: 6px !important; }
.chapter-top-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  padding: 8px 0;
}
.header-title-area {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1 1 auto;
  min-width: 0;
}
.chapter-badge-id {
  background: var(--primary); color: var(--color-bg-surface); font-weight: 800;
  font-size: 12px; padding: 4px 10px; border-radius: 6px;
  flex-shrink: 0;
}
.chapter-title-main {
  font-size: 24px;
  font-weight: 800;
  letter-spacing: -0.5px;
  color: var(--color-text-strong, #0f172a);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.header-actions-area {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  flex-shrink: 0;
}
.external-select {
  width: 120px;
}
.meta-row { margin-bottom: 8px; }
.meta-card {
  display: flex; align-items: center; gap: 16px; padding: 16px 20px;
  border: 1px solid var(--border-light); border-radius: 12px;
  background: var(--bg-card); box-shadow: var(--shadow-sm);
}
.m-card-icon { display: grid; place-items: center; width: 42px; height: 42px; border-radius: 10px; font-size: 18px; }
.m-blue { background: #eaf6fc; color: #2e5f75; }
.m-orange { background: #fdf2eb; color: var(--primary); }
.m-green { background: #f0f9eb; color: #52c41a; }
.m-red { background: #fef0f0; color: #f56c6c; }
.m-val { font-size: 20px; font-weight: 800; color: #1a2129; }
.m-lbl { font-size: 12px; color: var(--text-muted); margin-top: 2px; }

.detail-tabs-panel { padding: 24px; }
.custom-detail-tabs :deep(.el-tabs__header) { margin-bottom: 24px; }

.summary-container { padding: 10px 20px; }
.md-preview :deep(.md-h3) {
  font-size: 18px; font-weight: 700; color: #1a2129;
  margin: 24px 0 12px; border-left: 3px solid var(--primary); padding-left: 10px;
}
.md-preview :deep(.md-p) { font-size: 15px; line-height: 1.7; color: var(--text-main); margin-bottom: 14px; }
.md-preview :deep(.md-ul) { margin-bottom: 16px; padding-left: 20px; }
.md-preview :deep(.md-li) { font-size: 14px; line-height: 1.7; color: var(--text-main); margin-bottom: 8px; }

.continuity-tab-content { display: flex; flex-direction: column; gap: 24px; }
.audit-status-bar {
  display: flex; align-items: center; gap: 12px;
  padding: 16px 20px; border-radius: 10px; font-size: 14px;
}
.audit-status-bar.risk-低 { background: #f0f9eb; color: #52c41a; border: 1px solid rgba(82, 196, 26, 0.15); }
.audit-status-bar.risk-高 { background: #fef0f0; color: #f56c6c; border: 1px solid rgba(245, 108, 108, 0.15); }
.audit-issues-block { display: flex; flex-direction: column; gap: 14px; }
.sub-section-title { font-size: 15px; font-weight: 700; color: #1a2129; }
.issues-card-list { display: flex; flex-direction: column; gap: 10px; }
.issue-detail-card {
  display: flex; gap: 12px; padding: 14px 18px; background: #fafafa;
  border-left: 4px solid var(--primary); border-radius: 0 8px 8px 0;
  border-top: 1px solid var(--border-light); border-right: 1px solid var(--border-light);
  border-bottom: 1px solid var(--border-light);
}
.issue-detail-card.warning { border-left-color: #e6a23c; }
.issue-badge {
  font-size: 11px; font-weight: 700; color: var(--primary);
  background: var(--primary-light); padding: 2px 8px; border-radius: 4px; height: 20px;
}
.issue-detail-card.warning .issue-badge { color: #e6a23c; background: #fdf6ec; }
.issue-desc-text { font-size: 13px; line-height: 1.5; color: var(--text-main); }
.success-audit-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 12px; padding: 40px; border: 1px dashed var(--border-light);
  border-radius: 10px; color: var(--text-muted); background: #fafaf9;
}
.success-audit-state .el-icon { font-size: 36px; color: #52c41a; }
.success-audit-state p { font-size: 13px; }

.state-update-content { display: flex; flex-direction: column; gap: 20px; }
.state-update-summary {
  background: #fafafa; border: 1px solid var(--border-light);
  padding: 12px 18px; border-radius: 8px; font-size: 14px;
}
.state-blocks-container { display: flex; flex-direction: column; gap: 24px; }
.state-block { display: flex; flex-direction: column; gap: 12px; }
.state-title-icon { font-size: 14px; font-weight: 700; display: flex; align-items: center; gap: 8px; color: #1a2129; }
.state-items { display: grid; grid-template-columns: 1fr; gap: 12px; }
.sub-state-item { border: 1px solid var(--border-light); border-radius: 8px; padding: 14px 18px; background: var(--color-bg-surface); }
.sub-state-item.event { border-left: 3px solid #3498db; }
.sub-state-item.node { border-left: 3px solid #2ecc71; }
.sub-state-item.forego { border-left: 3px solid #9b59b6; }
.sub-state-header { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 12px; }
.s-id, .s-name { font-weight: 700; color: #1a2129; }
.s-characters, .s-type { color: var(--text-muted); }
.s-body { font-size: 13px; line-height: 1.5; color: var(--text-main); }
.s-status { font-size: 11px; font-weight: 600; padding: 2px 6px; border-radius: 4px; }
.s-status.open { background: #fdf6ec; color: #e6a23c; }
.s-status.closed { background: #f0f9eb; color: #52c41a; }

.raw-json-collapse { margin-top: 32px; border: 1px solid var(--border-light); border-radius: 8px; overflow: hidden; }
.raw-json-collapse :deep(.el-collapse-item__header) { padding: 0 16px; font-size: 12px; color: var(--text-muted); background-color: #fafafa; }
.raw-json-collapse :deep(.el-collapse-item__content) { padding: 16px; background-color: #f7f7f7; }
.raw-json-pre { font-family: var(--font-mono); font-size: 12px; color: #333333; white-space: pre-wrap; line-height: 1.5; }

.empty-state-card {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 12px; padding: 40px; color: var(--text-muted); text-align: center;
}
</style>
